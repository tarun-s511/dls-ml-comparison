# DLS vs. ML-Based Resource Estimation in Cricket

This project implements and compares three different methods for estimating a team's run-scoring potential (resource-equivalent) from any given match state in limited-overs (T20) cricket:

1. **Baseline**: Coded implementation of the DLS Standard Edition resource table using exponential decay.
2. **Model A (Over-level ML)**: An XGBoost regressor using features aggregated per over.
3. **Model B (Delivery-level ML)**: An XGBoost regressor using features at per-ball granularity, incorporating contextual player/venue ratings and rolling ball-by-ball streaks.

All three systems are evaluated on the same simulated-interruption task using a deterministic test split (hash-based by `match_id` to prevent data leakage).

---

## 📋 Directory Structure

- `data/`
  - `raw/`: Raw JSON zip files from Cricsheet.
  - `interim/`: Parsed tabular files (e.g. `ball_by_ball.parquet`, ratings parquet).
  - `processed/`: Final modeling-ready parquet files.
- `notebooks/`: The 9-step execution notebooks.
- `reports/`
  - `figures/`: Training, residual, calibration, and feature importance plots.
  - `tables/`: Generated evaluation CSV files and significance results.
- `src/common/`
  - `config.py`: Path constants and feature list configuration.
  - `dls_lookup.py`: DLS decay lookup logic.
  - `ratings.py`: Chronological player/venue ratings updates (no data leakage).
  - `nb_generator.py`: Build script to compile all notebooks.
  - `run_pipeline.py`: Programmatic execution runner.

---

## 📈 Evaluation Results

The models were evaluated by sampling 5 random interruption states for each match in the test set. The results are summarized below:

| Method | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | Prediction Bias |
| :--- | :---: | :---: | :---: |
| **DLS Baseline** | 22.41 runs | 31.83 runs | -8.81 runs |
| **Model A (Over-level ML)** | 15.65 runs | 22.95 runs | -1.16 runs |
| **Model B (Delivery-level ML)** | **15.54 runs** | **22.85 runs** | -1.35 runs |

### 🔬 Wilcoxon Signed-Rank Test

We performed a paired Wilcoxon signed-rank test on the absolute errors of Model A vs. Model B to determine if delivery-level features yield a statistically significant improvement:

- **Wilcoxon Test Statistic**: `11,149,885.5`
- **p-value**: `0.00316`
- **Statistical Significance**: **Yes (p < 0.05)**. Model B's delivery-level streaks and spell metrics provide a statistically significant reduction in prediction error compared to Model A's over-level aggregates.

---

## 🚀 Execution Guide

To regenerate the notebooks and run the entire pipeline top-to-bottom:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   brew install libomp  # Required for XGBoost C library on macOS
   ```
2. **Generate Jupyter Notebooks**:
   ```bash
   python3 src/common/nb_generator.py
   ```
3. **Execute the Entire Pipeline**:
   ```bash
   python3 src/common/run_pipeline.py
   ```
   Or execute a specific notebook step (1 to 9):
   ```bash
   python3 src/common/run_pipeline.py --step 5
   ```
