| metric | gemini-3.8-flash K1 (n=150) | gemini-3.8-flash K2 (n=150) | gemini-3.8-flash K2_crop (n=150) | gemini-3.8-flash K3 (n=150) |
|---|---|---|---|---|
| 1. valid output (%) | 100.0 | 100.0 | 99.3 | 99.3 |
| 2. shape count correct (%) | 90.0 | 98.7 | 96.7 | 89.3 |
| 3. action count within +/-1 (%) | 82.0 | 83.3 | 86.7 | 81.3 |
| 4a. action type accuracy, given order (%) | 74.0 | 77.8 | 79.7 | 71.5 |
| 4a'. action type accuracy, best alignment (%) | 74.5 | 79.7 | 80.9 | 72.9 |
| 4b. style accuracy, given order (%) | 60.0 | 63.5 | 63.2 | 55.8 |
| 4b'. style accuracy, best alignment (%) | 65.9 | 68.7 | 70.4 | 58.3 |
| 4c. number accuracy exact, given order (%) | 23.5 | 26.1 | 28.5 | 8.5 |
| 4c'. number accuracy exact, best alignment (%) | 27.4 | 29.4 | 33.9 | 10.0 |
| 4d. number accuracy within 0.02, given order (%) | 24.2 | 26.8 | 29.1 | 8.8 |
| 4d'. number accuracy within 0.02, best alignment (%) | 28.5 | 30.7 | 34.9 | 10.4 |
| 5. exact match (%) | 4.0 | 3.3 | 4.7 | 0.7 |
| 6. edit distance, given order (actions, mean) | 7.1 | 6.7 | 6.7 | 7.9 |
| 6'. edit distance, best alignment (actions, mean) | 6.6 | 6.3 | 6.1 | 7.8 |
| style accuracy, best minus given (points) | 6.0 | 5.2 | 7.2 | 2.4 |
| thought tokens, mean | 1933 | 1174 | 2084 | 1733 |
| baseline, style accuracy: random | 20.0 | 20.0 | 20.0 | 20.0 |
| baseline, style accuracy: majority in train, ff (square) | 20.6 | 20.6 | 20.6 | 20.6 |
| baseline, style accuracy: majority in train, bd (normal) | 67.5 | 67.5 | 67.5 | 67.5 |
| baseline, style accuracy: majority in train, hd (normal) | 64.9 | 64.9 | 64.9 | 64.9 |

Per type: style accuracy best alignment / given order | action count within 1 | exact | passes its baseline + 10 points?
- gemini-3.8-flash K1 bd (n=60): 62.4 / 62.1 | 66.7 | 0.0 | no (baseline 67.5)
- gemini-3.8-flash K1 ff (n=60): 67.1 / 52.2 | 91.7 | 8.3 | yes (baseline 20.6)
- gemini-3.8-flash K1 ff_1shape (n=30): 58.2 / 45.0 | 86.7 | 10.0 | yes (baseline 20.6)
- gemini-3.8-flash K1 ff_2shape (n=30): 76.0 / 59.5 | 96.7 | 6.7 | yes (baseline 20.6)
- gemini-3.8-flash K1 hd (n=30): 70.6 / 71.1 | 93.3 | 3.3 | no (baseline 64.9)
- gemini-3.8-flash K2 bd (n=60): 63.3 / 61.7 | 66.7 | 0.0 | no (baseline 67.5)
- gemini-3.8-flash K2 ff (n=60): 64.5 / 57.2 | 93.3 | 6.7 | yes (baseline 20.6)
- gemini-3.8-flash K2 ff_1shape (n=30): 62.0 / 54.5 | 90.0 | 6.7 | yes (baseline 20.6)
- gemini-3.8-flash K2 ff_2shape (n=30): 66.9 / 59.9 | 96.7 | 6.7 | yes (baseline 20.6)
- gemini-3.8-flash K2 hd (n=30): 87.8 / 79.6 | 96.7 | 3.3 | yes (baseline 64.9)
- gemini-3.8-flash K2_crop bd (n=60): 65.9 / 62.4 | 76.7 | 0.0 | no (baseline 67.5)
- gemini-3.8-flash K2_crop ff (n=60): 70.7 / 56.2 | 91.7 | 10.0 | yes (baseline 20.6)
- gemini-3.8-flash K2_crop ff_1shape (n=30): 67.6 / 53.7 | 90.0 | 10.0 | yes (baseline 20.6)
- gemini-3.8-flash K2_crop ff_2shape (n=30): 73.8 / 58.7 | 93.3 | 10.0 | yes (baseline 20.6)
- gemini-3.8-flash K2_crop hd (n=30): 78.6 / 78.6 | 96.7 | 3.3 | yes (baseline 64.9)
- gemini-3.8-flash K3 bd (n=60): 65.2 / 60.5 | 68.3 | 0.0 | no (baseline 67.5)
- gemini-3.8-flash K3 ff (n=60): 43.1 / 43.1 | 91.7 | 0.0 | yes (baseline 20.6)
- gemini-3.8-flash K3 ff_1shape (n=30): 38.7 / 38.7 | 90.0 | 0.0 | yes (baseline 20.6)
- gemini-3.8-flash K3 ff_2shape (n=30): 47.5 / 47.5 | 93.3 | 0.0 | yes (baseline 20.6)
- gemini-3.8-flash K3 hd (n=30): 74.6 / 71.8 | 86.7 | 3.3 | no (baseline 64.9)

Decision rule (3a): 'cannot read' only if, in every type, style accuracy (best alignment) is below the type's majority baseline + 10 points and action count within 1 is below 50%.
