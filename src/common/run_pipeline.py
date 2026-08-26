import os
import sys
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

# Ensure python path includes src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

notebooks = [
    "01_ingestion.ipynb",
    "02_cleaning_eda.ipynb",
    "03_dls_baseline.ipynb",
    "04_contextual_ratings.ipynb",
    "05_feature_engineering.ipynb",
    "06_model_training_over.ipynb",
    "07_model_training_delivery.ipynb",
    "08_evaluation.ipynb",
    "09_analysis_report.ipynb"
]

notebooks_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "notebooks")

def run_notebook(notebook_filename):
    notebook_path = os.path.join(notebooks_dir, notebook_filename)
    print("=" * 60)
    print(f"Executing: {notebook_filename}")
    print("=" * 60)
    
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
            
        # Create execution preprocessor
        ep = ExecutePreprocessor(timeout=1800, kernel_name='python3')
        
        # Preprocess / execute
        ep.preprocess(nb, {'metadata': {'path': notebooks_dir}})
        
        # Save back the executed notebook
        with open(notebook_path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
            
        print(f"Successfully completed: {notebook_filename}\n")
        return True
    except Exception as e:
        print(f"ERROR executing {notebook_filename}: {e}\n")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the DLS vs ML cricket resource estimation pipeline.")
    parser.add_argument("--step", type=int, default=None, help="Specific step to run (1-9)")
    args = parser.parse_args()
    
    if args.step is not None:
        if 1 <= args.step <= len(notebooks):
            success = run_notebook(notebooks[args.step - 1])
            sys.exit(0 if success else 1)
        else:
            print(f"Invalid step: {args.step}. Must be between 1 and 9.")
            sys.exit(1)
            
    # Run entire pipeline
    for nb in notebooks:
        success = run_notebook(nb)
        if not success:
            print("Pipeline aborted due to error.")
            sys.exit(1)
            
    print("Pipeline completed successfully!")
