# LogSense — Synthetic Test Datasets

Five datasets, one per test scenario from the spec. Save each as its own `.log` file so you can feed them individually during Phase 1/4 testing.

---

## Dataset 1 — `sample_clean_spike.log`
Plenty of neighbor hours around the spike → should trigger HIGH confidence z-score detection.
Spike hour: 15:00, dominant pattern: Database.

```
2026-08-16 11:03:12 INFO Request handled successfully
2026-08-16 11:15:44 WARNING High memory usage detected
2026-08-16 11:22:01 ERROR API request failed: 500 Internal Server Error
2026-08-16 11:45:19 INFO Health check passed
2026-08-16 12:01:33 ERROR API request failed: 500 Internal Server Error
2026-08-16 12:18:07 INFO Request handled successfully
2026-08-16 12:34:52 WARNING Slow query detected
2026-08-16 12:50:11 ERROR API request failed: timeout
2026-08-16 13:02:45 INFO Health check passed
2026-08-16 13:19:28 ERROR Auth token expired
2026-08-16 13:33:14 INFO Request handled successfully
2026-08-16 13:47:56 ERROR API request failed: 500 Internal Server Error
2026-08-16 13:58:02 WARNING High memory usage detected
2026-08-16 14:04:19 ERROR Auth token expired
2026-08-16 14:15:33 INFO Request handled successfully
2026-08-16 14:22:47 ERROR API request failed: timeout
2026-08-16 14:38:01 INFO Health check passed
2026-08-16 14:51:22 ERROR Database connection timeout
2026-08-16 15:00:04 ERROR Database connection timeout
2026-08-16 15:01:18 ERROR Database connection timeout
2026-08-16 15:02:33 ERROR Database connection timeout
2026-08-16 15:03:47 ERROR Database connection timeout
2026-08-16 15:05:02 ERROR Database connection timeout
2026-08-16 15:06:19 ERROR Database connection timeout
2026-08-16 15:07:31 ERROR Database connection timeout
2026-08-16 15:08:44 ERROR Database connection timeout
2026-08-16 15:09:58 ERROR Database connection timeout
2026-08-16 15:11:12 ERROR Database connection timeout
2026-08-16 15:12:27 ERROR Database connection timeout
2026-08-16 15:13:41 ERROR Database connection timeout
2026-08-16 15:14:55 ERROR Database connection timeout
2026-08-16 15:16:09 ERROR Database connection timeout
2026-08-16 15:17:23 ERROR Database connection timeout
2026-08-16 15:18:38 ERROR Database connection timeout
2026-08-16 15:19:52 ERROR API request failed: 503 Service Unavailable
2026-08-16 15:21:07 ERROR Database connection timeout
2026-08-16 15:22:21 ERROR Database connection timeout
2026-08-16 15:23:35 ERROR Database connection timeout
2026-08-16 15:24:49 ERROR Database connection timeout
2026-08-16 15:26:03 ERROR Database connection timeout
2026-08-16 15:27:18 ERROR Database connection timeout
2026-08-16 15:28:32 ERROR Database connection timeout
2026-08-16 15:29:46 ERROR Database connection timeout
2026-08-16 15:31:01 ERROR Database connection timeout
2026-08-16 15:32:15 ERROR Database connection timeout
2026-08-16 15:33:29 ERROR Database connection timeout
2026-08-16 15:34:44 ERROR Database connection timeout
2026-08-16 15:35:58 ERROR Database connection timeout
2026-08-16 15:37:12 ERROR Database connection timeout
2026-08-16 15:38:27 ERROR Database connection timeout
2026-08-16 15:39:41 ERROR Database connection timeout
2026-08-16 15:41:55 ERROR Database connection timeout
2026-08-16 15:43:09 ERROR Database connection timeout
2026-08-16 16:02:14 INFO Health check passed
2026-08-16 16:15:33 ERROR API request failed: timeout
2026-08-16 16:28:47 INFO Request handled successfully
2026-08-16 16:41:02 WARNING Slow query detected
2026-08-16 16:55:19 ERROR Auth token expired
2026-08-16 17:03:44 INFO Health check passed
2026-08-16 17:18:22 ERROR API request failed: 500 Internal Server Error
2026-08-16 17:31:08 INFO Request handled successfully
2026-08-16 17:47:53 ERROR Database connection timeout
2026-08-16 18:02:17 INFO Health check passed
```

Expected: peak/spike hour = 15:00, dominant pattern = Database, confidence = HIGH, severity = Critical.

---

## Dataset 2 — `sample_no_spike.log`
Stable traffic, no anomaly. Confirms the UI shows a clean green/normal state, not a broken empty state.

```
2026-08-16 09:04:11 INFO Request handled successfully
2026-08-16 09:18:29 ERROR API request failed: timeout
2026-08-16 09:33:47 INFO Health check passed
2026-08-16 09:51:02 WARNING Slow query detected
2026-08-16 10:07:18 ERROR Auth token expired
2026-08-16 10:22:36 INFO Request handled successfully
2026-08-16 10:39:54 ERROR Database connection timeout
2026-08-16 10:55:11 INFO Health check passed
2026-08-16 11:12:29 ERROR API request failed: 500 Internal Server Error
2026-08-16 11:28:47 INFO Request handled successfully
2026-08-16 11:44:02 WARNING High memory usage detected
2026-08-16 12:01:18 ERROR Auth token expired
2026-08-16 12:19:36 INFO Health check passed
2026-08-16 12:36:54 ERROR API request failed: timeout
2026-08-16 12:53:11 INFO Request handled successfully
2026-08-16 13:09:29 ERROR Database connection timeout
2026-08-16 13:27:47 INFO Health check passed
2026-08-16 13:44:02 WARNING Slow query detected
2026-08-16 14:01:18 ERROR API request failed: 500 Internal Server Error
2026-08-16 14:19:36 INFO Request handled successfully
```

Expected: no hour meaningfully deviates from the others — no spike flagged, status = Normal.

---

## Dataset 3 — `sample_multi_spike.log`
Two separate spike windows in different hours. Confirms multiple incident cards render without clobbering each other.

```
2026-08-16 09:04:11 INFO Request handled successfully
2026-08-16 09:18:29 ERROR API request failed: timeout
2026-08-16 09:33:47 INFO Health check passed
2026-08-16 10:07:18 ERROR Auth token expired
2026-08-16 10:22:36 INFO Request handled successfully
2026-08-16 11:00:04 ERROR Auth token expired: invalid signature
2026-08-16 11:01:18 ERROR Auth token expired: invalid signature
2026-08-16 11:02:33 ERROR Auth token expired: invalid signature
2026-08-16 11:03:47 ERROR Auth token expired: invalid signature
2026-08-16 11:05:02 ERROR Auth token expired: invalid signature
2026-08-16 11:06:19 ERROR Auth token expired: invalid signature
2026-08-16 11:07:31 ERROR Auth token expired: invalid signature
2026-08-16 11:08:44 ERROR Auth token expired: invalid signature
2026-08-16 11:09:58 ERROR Auth token expired: invalid signature
2026-08-16 11:11:12 ERROR Auth token expired: invalid signature
2026-08-16 11:12:27 ERROR Auth token expired: invalid signature
2026-08-16 11:13:41 ERROR Auth token expired: invalid signature
2026-08-16 11:14:55 ERROR Auth token expired: invalid signature
2026-08-16 11:16:09 ERROR Auth token expired: invalid signature
2026-08-16 11:17:23 ERROR Auth token expired: invalid signature
2026-08-16 11:18:38 ERROR Auth token expired: invalid signature
2026-08-16 11:19:52 ERROR Auth token expired: invalid signature
2026-08-16 11:21:07 ERROR Auth token expired: invalid signature
2026-08-16 11:22:21 ERROR Auth token expired: invalid signature
2026-08-16 11:23:35 ERROR Auth token expired: invalid signature
2026-08-16 12:02:14 INFO Health check passed
2026-08-16 12:15:33 ERROR API request failed: timeout
2026-08-16 12:41:02 WARNING Slow query detected
2026-08-16 13:03:44 INFO Health check passed
2026-08-16 13:18:22 ERROR API request failed: 500 Internal Server Error
2026-08-16 14:00:14 ERROR Database connection timeout
2026-08-16 14:01:33 ERROR Database connection timeout
2026-08-16 14:02:47 ERROR Database connection timeout
2026-08-16 14:04:02 ERROR Database connection timeout
2026-08-16 14:05:19 ERROR Database connection timeout
2026-08-16 14:06:31 ERROR Database connection timeout
2026-08-16 14:07:44 ERROR Database connection timeout
2026-08-16 14:08:58 ERROR Database connection timeout
2026-08-16 14:10:12 ERROR Database connection timeout
2026-08-16 14:11:27 ERROR Database connection timeout
2026-08-16 14:12:41 ERROR Database connection timeout
2026-08-16 14:13:55 ERROR Database connection timeout
2026-08-16 14:15:09 ERROR Database connection timeout
2026-08-16 14:16:23 ERROR Database connection timeout
2026-08-16 14:17:38 ERROR Database connection timeout
2026-08-16 14:18:52 ERROR Database connection timeout
2026-08-16 14:20:07 ERROR Database connection timeout
2026-08-16 14:21:21 ERROR Database connection timeout
2026-08-16 15:02:14 INFO Health check passed
2026-08-16 15:15:33 ERROR API request failed: timeout
2026-08-16 15:41:02 WARNING Slow query detected
2026-08-16 16:03:44 INFO Health check passed
```

Expected: two distinct incidents — Auth-category spike around 11:00, Database-category spike around 14:00.

---

## Dataset 4 — `sample_tiny.log`
Under 5 total lines. Confirms graceful LOW/MEDIUM confidence handling instead of a crash or a falsely confident HIGH claim.

```
2026-08-16 15:02:11 ERROR Database connection timeout
2026-08-16 15:04:33 ERROR Database connection timeout
2026-08-16 15:06:52 ERROR Database connection timeout
2026-08-16 16:01:14 INFO Health check passed
```

Expected: spike hour reported with confidence LOW or MEDIUM (not HIGH — there isn't enough surrounding data for a z-score), no crash.

---

## Dataset 5 — `sample_malformed.log`
Mixed valid and garbage lines. Confirms valid lines still get analyzed and the user sees a friendly warning, not a raw stack trace.

```
2026-08-16 15:02:11 ERROR Database connection timeout
this is not a valid log line at all
2026-08-16 15:04:33 ERROR Database connection timeout
2026-08-16T15:06:52Z BADLEVEL something went sideways here
2026-08-16 15:08:52 ERROR Database connection timeout

2026-08-16 15:11:19 WARNING High memory usage detected
###CORRUPTED_LINE###
2026-08-16 15:14:02 ERROR Database connection timeout
```

Expected: 5 valid entries parsed and analyzed correctly, 3 malformed lines skipped with a warning surfaced to the user (not a crash, not silently ignored with no indication).

---

## Dataset 6 (optional, for empty-input test)
Just submit an empty string / empty file through the UI directly — no file needed. Confirms a clear "please provide log data" message rather than a silent failure or ugly 500 error.
