# Safe Route Scoring Algorithm

## Goal

Given multiple routes from OSRM, calculate a **safety score** for each route and return the best route.

This is a practical heuristic approach: fast, explainable, and easy to improve later.

---

# Overall Idea

For every available route:

1. Read route geometry (points on the road path)
2. Compare route points with:

   * danger zones
   * safe zones
3. Add penalties / bonuses
4. Penalize unnecessary detours
5. Choose the route with the highest final score

---

# Final Score Formula

```text
finalScore = safeBonus - riskPenalty - extraDistancePenalty - extraTimePenalty
```

Higher score = better route.

---

# Input Data Needed

## 1. Routes from OSRM

Use alternatives from OSRM.

Each route gives:

* geometry
* distance
* duration

## 2. Danger Zones

Example:

```json
{
  "name": "ISBT",
  "lat": 30.2888,
  "lng": 78.0435,
  "radius": 700,
  "level": "high"
}
```

## 3. Safe Zones

Example:

```json
{
  "name": "Police Lines",
  "lat": 30.3168,
  "lng": 78.0505,
  "radius": 600,
  "level": "high"
}
```

---

# Step 1: Get Alternative Routes

Use OSRM:

```text
alternatives=true
overview=full
geometries=geojson
```

This returns multiple possible routes.

---

# Step 2: Sample Route Points

A route may contain many coordinates.

Do not process every point unless needed.

Use:

* every 10th point
  nor
* every 100 meters

This makes scoring faster.

---

# Step 3: Risk Penalty

For each sampled route point:

Check distance to each danger zone.

If point is inside zone radius:

```text
penalty += impact
```

## Simple Impact

```text
high = 10
medium = 6
low = 3
```

## Better Impact (Distance Based)

Closer to center = stronger risk.

```text
impact = weight * (1 - distance / radius)
```

Only apply when:

```text
distance < radius
```

---

# Step 4: Safe Bonus

For each sampled point:

Check distance to safe zones.

If inside radius:

```text
bonus += impact
```

Suggested weights:

```text
high = 8
medium = 5
low = 2
```

---

# Step 5: Penalize Long Detours

Safest route should not be absurdly long.

Compare with shortest route.

## Distance Penalty

```text
extraDistancePenalty = (routeDistance - shortestDistance) * factor
```

## Time Penalty

```text
extraTimePenalty = (routeTime - fastestTime) * factor
```

---

# Step 6: Pick Best Route

Compute score for each route.

Return route with highest score.

---

# Example

## Route A

* Risk = 20
* Safe = 8
* Extra Distance = 1

```text
Score = 8 - 20 - 1 = -13
```

## Route B

* Risk = 8
* Safe = 10
* Extra Distance = 3

```text
Score = 10 - 8 - 3 = -1
```

Route B is safer.

---

# Java-Style Pseudocode

```java
for (Route route : routes) {
    double score = 0;

    for (Point p : sampledPoints(route)) {
        score -= riskImpact(p, dangerZones);
        score += safeImpact(p, safeZones);
    }

    score -= extraDistance(route);
    score -= extraTime(route);

    route.setScore(score);
}

Route best = maxScore(routes);
```

---

# API Response Example

```json
{
  "bestRoute": { ... },
  "score": 12.4,
  "alternatives": [ ... ]
}
```

---

# Why This Approach Is Good

* Fast enough for real-time use
* Easy to debug
* Explainable to users/interviewers
* Works with mock data
* Easy to tune later
* Can evolve into ML later

---

# Future Improvements

* Time of day weighting (night = more risk)
* Live user reports
* Street lighting data
* CCTV presence
* Crime history density maps
* Weather effects
* ML ranking model

---

# Final Note

This is a decision heuristic, not a guarantee of safety. It helps rank routes by available signals.