# Modelling and accuracy ideas for larry-tracker

larry-tracker stores raw Find My reports and turns them into trips with two
fixed rules: a gap of more than 45 minutes starts a new trip, and a trip whose
last point is within 75 m of home is a round trip. Everything else is drawn as
reported. This document lists mathematical, stochastic and probabilistic
techniques that would make the positions more accurate and the behaviour
modelling more meaningful, and explains why each one fits this project's data.

## Why the data needs more than raw points

Three properties of Find My data drive every choice below:

- **Sparse, irregular sampling.** Reports arrive only when an Apple device
  passes within Bluetooth range of the tag. Gaps range from a couple of minutes
  to hours, and they are not evenly spaced. Methods that assume a fixed sample
  rate (moving averages, plain discrete-time filters) do not fit.
- **Noisy points with known uncertainty.** Every report carries
  `horizontal_accuracy` (metres) and `confidence`. That is unusual and valuable:
  the noise level is given per point, so a model can trust a 5 m report more
  than a 25 m one instead of treating them equally.
- **The position is the finder's, not the tag's.** A report is the location of
  the iPhone that heard the tag, so there is an extra, unreported offset of
  roughly 10-30 m (Bluetooth range). This is a systematic error on top of the
  reported accuracy.

A cat also behaves in a recognisable way: it has a home it returns to, rests
and explores in bursts, and favours a few places. Movement ecology, the field
that studies animal tracking data from collars, has well-tested methods for
exactly this kind of data, and most ideas below come from there.

---

## 1. Cleaning individual points

### 1.1 Inverse-variance weighting of near-duplicates

**What it is.** When several reports arrive close together in time and space,
merge them into one point whose position is a weighted average, with each
report's weight equal to `1 / sigma^2`, where `sigma` is its
`horizontal_accuracy`. The merged point's uncertainty is
`sigma_merged = 1 / sqrt(sum(1 / sigma_i^2))`, always smaller than any single
input.

**Why it is useful here.** The poller often stores two or three reports per
poll for nearly the same moment. Today they appear as separate points, which
adds jitter to the drawn path and inflates the computed distance. Weighting by
the accuracy Apple already provides is the statistically optimal way to
combine independent measurements, and it costs a few lines of code.

**Where it fits.** A pre-processing step in `trips.py`, before trip
segmentation.

### 1.2 Outlier rejection with speed and Mahalanobis gates

**What it is.** For each point, compute the speed needed to reach it from its
neighbours, and the distance to the predicted position divided by the combined
uncertainty (a Mahalanobis distance). Points that imply an impossible speed for
a cat, or lie many standard deviations from where the path predicts, are
flagged or dropped. A robust alternative is RANSAC or a median filter over a
short window.

**Why it is useful here.** A single bad report (a phone with a poor GPS fix, or
one moving fast past the cat) creates a long spike in the path and a fake jump
in distance and speed. The current quality filter only checks `confidence` and
a fixed accuracy ceiling; it cannot catch a point that is individually
"accurate" but inconsistent with its neighbours.

**Where it fits.** `filter_quality` in `trips.py`, extended from per-point
rules to neighbour-aware rules.

### 1.3 Kalman filter with RTS smoothing (recommended first step)

**What it is.** A Kalman filter tracks a hidden state, here position and
velocity, and updates it as each report arrives:

- **Predict:** move the state forward by the elapsed time `dt` with a
  constant-velocity model, and grow its uncertainty by process noise that
  scales with `dt`.
- **Update:** blend the prediction with the new report, weighting each by its
  uncertainty. The report's noise is its own `horizontal_accuracy`.

Because trips are analysed after the fact, the Rauch-Tung-Striebel (RTS)
smoother then runs backwards over the trip, so every estimate uses both earlier
and later reports.

**Why it is useful here.**

- It handles irregular gaps natively, since `dt` is part of the model.
- It uses the per-point accuracy directly, which is exactly the information
  Find My provides.
- The output is a smooth, physically plausible path with an uncertainty
  ellipse at every point, instead of a zigzag between noisy fixes.
- Trip distance and average speed become far more realistic. Raw zigzags
  systematically overestimate distance, because noise adds length.
- It is well understood, fast, and available in `filterpy` or `pykalman`.

**Where it fits.** A new `smoothing.py` in location-service, applied per trip.
The API could return both raw and smoothed paths so the UI can toggle between
them, which also makes a good before/after slide.

### 1.4 Particle filter with map constraints

**What it is.** A particle filter represents the cat's possible positions as
thousands of weighted samples ("particles"). Each step, particles move by a
random motion model, and are reweighted by how well they match the report and
any other knowledge, then resampled.

**Why it is useful here.** It can encode rules a Kalman filter cannot: the cat
cannot be in the canal, is unlikely to be in the middle of a main road, and is
more likely in gardens and parks. The map data already in the UI (water,
buildings, parks from the CARTO tiles) could supply those constraints. The
result is paths that respect geography rather than cutting across water.

**Trade-off.** More compute and more tuning than a Kalman filter. Worth it only
after the Kalman smoother is in place and its limits are visible.

---

## 2. Reconstructing the path between reports

### 2.1 Brownian bridge movement model

**What it is.** Between two consecutive reports, the animal's position is
modelled as a random walk pinned at both ends (a Brownian bridge). Halfway
between two reports, the most likely position is between them, with an
uncertainty that is largest mid-gap and shrinks to the reports' own accuracy at
each end. The spread is controlled by one fitted mobility parameter.

**Why it is useful here.** It is the standard method in animal ecology for
exactly the irregular, gappy fixes Find My produces. A straight line between
reports, which is what the map draws today, pretends to know the route. The
bridge says honestly "he was somewhere in this corridor", and the corridor
widens where data is thin. Integrated over a trip, it also gives a much better
estimate of where time was spent than the raw points (see 3.1).

### 2.2 Gaussian process regression

**What it is.** A Gaussian process treats the trajectory as a smooth random
function of time and fits it through the reports, weighting each by its
accuracy. It returns a mean path and a confidence band at every moment.

**Why it is useful here.** Similar benefits to the Brownian bridge, with control
over smoothness through the choice of kernel. Useful when you want a smooth
curve with honest uncertainty for display, or to resample a trip at regular
intervals for other analyses that need even timing.

---

## 3. Where Larry spends his time

### 3.1 Kernel density estimation (home range)

**What it is.** Place a small probability "bump" (a kernel, usually Gaussian) on
every location and sum them into a smooth density surface. The 50% contour
outlines the core area, where he spends half his time; the 95% contour is his
overall range. Kernel widths can follow each report's accuracy.

**Why it is useful here.** It answers the question owners actually ask: "where
does he usually go?" Individual trips are noisy; the density over weeks of data
is stable and readable. It is the standard "home range" analysis for collared
animals, so it is defensible in a presentation, and a heatmap with two contours
is a strong visual. `scipy.stats.gaussian_kde` is enough to start.

### 3.2 Clustering stop points (DBSCAN / HDBSCAN)

**What it is.** Density-based clustering groups points that are close in space
(and optionally time) and labels sparse points as noise. HDBSCAN does this
without a fixed distance threshold.

**Why it is useful here.** It turns thousands of points into a handful of named
places: "garden behind Hind Grove", "bench in Bartlett Park". Combined with the
place names in the vector map data, the UI could list favourite spots with
visit counts and typical times. It is also a sanity check on the mock data,
which should produce a few recurring hotspots, not uniform noise.

### 3.3 Minimum convex polygon

**What it is.** The smallest convex shape containing all (or 95%) of the
points.

**Why it is useful here.** The simplest territory measure, easy to explain, and
a baseline to show why the KDE is better (a convex polygon includes large areas
the cat never visits).

---

## 4. Behaviour and trip modelling

### 4.1 Hidden Markov model for behavioural states

**What it is.** An HMM assumes the cat is always in one of a few hidden states,
for example _resting_, _exploring_ and _travelling_, and switches between them
with fixed probabilities. Each state produces characteristic step lengths and
turning angles between consecutive points: short steps with random turns when
exploring, long straight steps when travelling, almost no movement when
resting. Fitting the model learns those distributions and switching
probabilities from the data. The Viterbi algorithm then labels each segment of
a trip with its most likely state.

**Why it is useful here.**

- It gives behavioural insight ("he spends 70% of outings exploring") rather
  than just lines on a map.
- It is a principled replacement for the fixed 45-minute trip rule: a trip
  becomes "leaves the resting-at-home state, returns to it", which adapts to
  each cat instead of a hand-picked constant.
- It is widely used in movement ecology (e.g. the `momentuHMM` R package), and
  `hmmlearn` covers the basics in Python.

### 4.2 Change-point detection

**What it is.** Algorithms that find the moments where a time series' statistics
change, such as Bayesian online change-point detection on speed.

**Why it is useful here.** A lighter alternative to the HMM for splitting trips
or detecting "started moving", without fitting a full state model.

### 4.3 Correlated random walk, fitted to real movement

**What it is.** A random walk where each step's length is drawn from a fitted
distribution (gamma or Weibull) and each turning angle from a von Mises
distribution, which makes direction persist from step to step.

**Why it is useful here.**

- Fitting it to real data summarises Larry's movement in a few parameters
  (typical step, how straight he walks), which can be compared over time or
  between cats.
- It replaces the current mock, a uniform random walk around home, with
  generated data that moves like a real animal. The demo and the tests would
  then exercise realistic paths.

### 4.4 Ornstein-Uhlenbeck process (random walk with a home)

**What it is.** A continuous-time random walk with a pull back towards a centre:
`dX = -theta (X - home) dt + sigma dW`. `theta` sets how strongly he is drawn
home; `sigma` sets how much he wanders. Because it is continuous-time, uneven
gaps between reports are handled exactly. The R package `ctmm` fits this
family of models to tracking data.

**Why it is useful here.** It is the simplest model that matches a cat's core
behaviour: wander, but keep coming back. It powers the "where is he now"
feature below, gives a principled home-range estimate, and makes an excellent
generator for realistic mock data.

---

## 5. Prediction and probabilities

### 5.1 "Where is he now?" with growing uncertainty

**What it is.** From the last report, propagate the position forward with the
Ornstein-Uhlenbeck or diffusion model. The result is a probability area that
widens with time since the last report and is pulled back towards home.

**Why it is useful here.** Find My data is always stale by minutes to hours.
Today the UI shows the last point as if it were current. A circle that grows
until the next report arrives is honest about that, and it is the kind of
feature that makes the project feel finished in a demo.

### 5.2 Round trips as a probability

**What it is.** Instead of "last point within 75 m", compute the probability
that the cat's true final position is within the home radius, using the last
point's accuracy (and the smoothed estimate from 1.3).

**Why it is useful here.** A 30 m-accuracy point 80 m from home is currently
"did not return home", which may well be wrong. "Round trip, 85% likely" is
more truthful and avoids flip-flopping labels near the boundary.

### 5.3 Survival analysis of time away

**What it is.** Model the duration of outings with a distribution such as
Weibull, and estimate the probability that an outing lasts longer than a given
time.

**Why it is useful here.** It turns "he has been out 3 hours" into "fewer than
5% of his outings last this long", which is a sound basis for an alert, rather
than a fixed timeout.

### 5.4 Markov chain over places

**What it is.** Discretise the area into cells or the clusters from 3.2, and
estimate the probability of moving from each place to every other.

**Why it is useful here.** It predicts the likely next place and shows routines,
such as "from the park he usually goes to the garden, then home".

### 5.5 Poisson model of report arrivals

**What it is.** Model the rate at which reports arrive as a Poisson process,
possibly varying by time of day and area.

**Why it is useful here.** It separates two causes of silence: Larry is
somewhere with no passing iPhones, or the pipeline is broken (as it currently is
with Apple's login change). Knowing the expected rate makes "no reports for 2
hours" either normal or a real alarm.

---

## Suggested order

| Step | Technique                                                      | Effort      | Payoff                                                            |
| ---- | -------------------------------------------------------------- | ----------- | ----------------------------------------------------------------- |
| 1    | Kalman filter + RTS smoother, noise from `horizontal_accuracy` | Low-medium  | Smoother paths, realistic distances and speeds; before/after demo |
| 2    | KDE home range heatmap                                         | Low         | Best single visual; answers "where does he go"                    |
| 3    | Ornstein-Uhlenbeck or correlated random walk mock              | Low-medium  | Realistic demo and test data                                      |
| 4    | Probabilistic round trips and "where is he now"                | Medium      | Honest uncertainty in the UI                                      |
| 5    | HMM behavioural states                                         | Medium-high | Behaviour insight; principled trip splitting                      |
| 6    | Brownian bridge, particle filter, survival and Markov models   | High        | Deeper analysis once real data flows                              |

Useful libraries: `filterpy` or `pykalman` (Kalman), `scipy` (KDE,
distributions), `scikit-learn` / `hdbscan` (clustering), `hmmlearn` (HMMs),
`movingpandas` (trajectory handling). For reference implementations of
continuous-time movement models, the R package `ctmm`.

All of these work on the mock data today, so they can be built and demonstrated
before the real Find My pipeline is restored.
