import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

INPUT_XLSX = "WAXS_1d.xlsx"   
LAMBDA = 2e5                  
P_LOWER = 0.01                
N_ITER = 12                   


os.makedirs("plots", exist_ok=True)

def asls_baseline(y, lam=2e5, p=0.01, niter=12):
    """稳健 AsLS 基线校正 (Eilers & Boelens)"""
    y = np.asarray(y, dtype=float)
    n = y.size
    if n < 5:
        return np.zeros_like(y)
    D = np.zeros((n-2, n))
    for i in range(n-2):
        D[i, i:i+3] = [1, -2, 1]
    DtD = lam * (D.T @ D)
    w = np.ones(n)
    for _ in range(niter):
        W = np.diag(w)
        Z = W + DtD
        b = w * y
        z = np.linalg.solve(Z, b)
        w = p * (y > z) + (1 - p) * (y <= z)
    return z

def herman_factor(chi_deg, inten_corr):
    """计算 Herman 因子"""
    chi = np.deg2rad(chi_deg)
    dchi = np.gradient(chi)
    num = np.sum(inten_corr * (np.cos(chi)**2) * dchi)
    den = np.sum(inten_corr * dchi)
    if den <= 0:
        return np.nan
    cos2 = num / den
    return (3*cos2 - 1)/2

def load_two_cols_numeric(df):
    sub = df.iloc[:, :2].copy()
    for c in sub.columns:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    sub = sub.dropna().sort_values(by=sub.columns[0])
    return sub

def process_sheet(name, df):
    sub = load_two_cols_numeric(df)
    if sub.empty or sub.shape[0] < 10:
        return {"sheet": name, "status": "No valid data", "Herman": np.nan}

    angles = sub.iloc[:, 0].to_numpy()
    intens = sub.iloc[:, 1].to_numpy()

    # 将 -90~90 对称扩展为 0~180
    angles = np.abs(angles)
    angles = np.concatenate([angles, 180 - angles])
    intens = np.concatenate([intens, intens[::-1]])

    # 基线校正
    baseline = asls_baseline(intens, lam=LAMBDA, p=P_LOWER, niter=N_ITER)
    corrected = intens - baseline
    corrected[corrected < 0] = 0

    # Herman 因子
    f = herman_factor(angles, corrected)

    # 绘图
    plt.figure(figsize=(7, 4))
    plt.plot(angles, intens, label="Raw (Symmetric Extended)")
    plt.plot(angles, baseline, label="Baseline")
    plt.plot(angles, corrected, label="Corrected")
    plt.xlabel("Azimuth angle (deg)")
    plt.ylabel("Intensity (a.u.)")
    plt.title(f"{name}  |  Herman = {f:.4f}" if np.isfinite(f) else f"{name}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join("plots", f"{name}_profile.png"), dpi=180)
    plt.close()

    return {
        "sheet": name,
        "points": len(angles),
        "angle_min": float(angles.min()),
        "angle_max": float(angles.max()),
        "Herman": float(f) if np.isfinite(f) else np.nan,
        "status": "OK"
    }

def main():
    xls = pd.ExcelFile(INPUT_XLSX)
    rows = []
    for s in xls.sheet_names:
        df = pd.read_excel(INPUT_XLSX, sheet_name=s).dropna(axis=1, how="all").dropna(axis=0, how="all")
        rows.append(process_sheet(s, df))
    out = pd.DataFrame(rows)
    out.to_csv("Qiyuan_Xue_Herman_results.csv", index=False)
    print(out.to_string(index=False))
    print("\n✅ 结果已保存至 'Qiyuan_Xue_Herman_results.csv'，曲线图见 './plots/'")

if __name__ == "__main__":
    main()