import pandas as pd
import sys

def main():
    try:
        df = pd.read_csv('data/training_data.csv')
        total = len(df)
        defect_count = df['defect_label'].sum()
        rate = defect_count / total
        print(f"Total Rows: {total}")
        print(f"Defect Positives: {defect_count}")
        print(f"Defect Rate: {rate:.4f} ({rate*100:.2f}%)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
