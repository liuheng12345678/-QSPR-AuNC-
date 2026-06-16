[README.md](https://github.com/user-attachments/files/28982094/README.md)
# -QSPR-AuNC-# AuNC 结构参数预测代码

## 1. 代码要解决什么问题

本代码包重点回答：

```text
如果目标是高活性，AuNC 的结构参数应该优先参考哪些范围和组合？
如果目标是高分散性 / 高稳定性，AuNC 的结构参数应该优先参考哪些范围和组合？
```

因此，代码输出的是结构参数建议，例如 core、ligand、粒径、DLS、Zeta 电位、发射峰、合成温度、反应时间和 pH 等。

## 2. 数据表

```text
aunc_data.csv
```

已有文献数据，用于建立模型和总结参数规律。每条记录保留 `source_batch`、`reference_id`、`DOI` 和 `paper_title`，可以追溯到文献来源。

```text
candidate_data.csv
```

待预测候选结构表。后续如果想让代码预测多个新候选结构，就把候选 AuNC 的结构参数填进这张表。

不要把新候选结构写进 `aunc_data.csv`。  
`aunc_data.csv` 是训练数据，`candidate_data.csv` 是待预测数据。

## 3. 两份核心代码

```text
predict_high_activity_structure.py
```

高活性 AuNC 结构参数预测代码。

它使用文献中的 TMB/POD 活性标签，例如：

- Km_TMB_mM；
- Km_H2O2_mM；
- Vmax_TMB_M_s；
- Vmax_H2O2_M_s；
- absorbance_TMB_652nm。

其中 Km 越低越好，Vmax 越高越好。代码根据这些标签筛选和建模，输出高活性方向值得参考的结构参数。

```text
predict_high_dispersity_structure.py
```

高分散性 / 高稳定性 AuNC 结构参数预测代码。

由于目前 PDI、水凝胶保持率、湿干循环保持率等直接标签仍不足，这份代码主要根据已有的 DLS、TEM、粒径标准差、Zeta 电位、发射峰和合成条件等字段，总结推荐参数范围，并对候选结构进行稳定性范围匹配。

## 4. 运行方法

双击：

```text
install.bat
```

再双击：

```text
run.bat
```

或者在命令行运行：

```bash
python -m pip install -r requirements.txt
python run_all.py
```

运行后会生成 `results/` 文件夹。

## 5. 主要输出

高活性方向：

```text
results/high_activity_model_summary.csv
results/high_activity_structure_recommendations.csv
results/high_activity_parameter_ranges.csv
results/high_activity_candidate_predictions.csv
results/top_high_activity_candidates.csv
```

其中：

- `high_activity_structure_recommendations.csv` 是根据已有文献数据得到的高活性结构参数参考；
- `high_activity_parameter_ranges.csv` 是高活性方向的参数范围；
- `top_high_activity_candidates.csv` 是对 `candidate_data.csv` 中新候选结构的预测排序。

高分散性 / 稳定性方向：

```text
results/high_dispersity_parameter_ranges.csv
results/high_dispersity_structure_recommendations.csv
results/high_dispersity_candidate_scores.csv
results/top_high_dispersity_candidates.csv
```

其中：

- `high_dispersity_parameter_ranges.csv` 是高分散性 / 稳定性参数范围；
- `high_dispersity_structure_recommendations.csv` 是文献支持的候选结构体系；
- `top_high_dispersity_candidates.csv` 是对 `candidate_data.csv` 中新候选结构的稳定性匹配排序。

## 6. 怎么插入新候选结构

打开：

```text
candidate_data.csv
```

每一行填一个候选 AuNC。推荐填写：

```text
candidate_id
core
ligand
ligand_family
ligand_ratio
diameter_TEM_nm
diameter_DLS_nm
diameter_sd_nm
zeta_mV
emission_peak_nm
synthesis_temperature_C
synthesis_time_h
pH
AuNC_type
is_pure_AuNC_or_composite
composite_type
carrier_or_matrix
note
```

只填结构参数 X，不填 Km、Vmax、保持率等性能 y。  
运行代码后，程序会预测和排序候选结构。

## 7. 当前结果如何理解

这套代码的逻辑是：

```text
已有文献数据 → 学习或总结结构参数与性能之间的关系
目标是高活性 / 高分散性 → 输出更值得参考的结构参数
新候选结构 → 预测并排序
```

高活性方向已有一定数量的 Km 和 Vmax 标签，因此可以进行小样本 Ridge 回归。  
高分散性方向直接监督标签仍不足，因此采用参数范围总结和候选结构范围匹配。

结果用于指导后续实验优先级，不代表已经证明某个 AuNC 结构最优。

## 8. 局限性

当前代码和结果仍有以下限制：

1. 文献样本量较小；
2. 不同文献的实验条件不完全一致；
3. 部分性能标签样本数不足；
4. 高分散性 / 水凝胶稳定性方向的 retention 类标签较少；
5. 部分模型交叉验证 R² 不理想；
6. 输出结果只能用于初步筛选，不能替代后续实验验证。

因此，所有推荐结果都应作为合成和实验设计的优先级参考，而不是最终结论。

---

## 9. 后续工作

后续如果继续完善模型，可以重点补充以下数据：

- PDI；
- Zeta 电位；
- 荧光保持率；
- 湿干循环保持率；
- 水凝胶信号保持率；
- 模拟汗液和河水中的稳定性数据；
- 更标准化的 AuNC 合成条件和表征数据。

当数据量进一步增加后，可以尝试：

- 随机森林；
- PLS；
- 表格型神经网络；
- 图神经网络；
- 结构—性能联合预测模型。

但在当前阶段，主模型仍以 Ridge 回归和参数范围推荐为主。

---

## 10. 总结

本代码包完成了一个可运行、可追溯、可复现的 AuNC QSPR 小样本分析流程。

本阶段完成的工作包括：

1. 将两批文献检索结果整理为统一数据表 `aunc_data.csv`；
2. 保留每条数据对应的 `reference_id`、`DOI` 和文献题名；
3. 编写高活性 AuNC 小样本预测代码 `predict_high_activity_structure.py`；
4. 编写高分散性 / 稳定性参数范围推荐代码 `predict_high_dispersity_structure.py`；
5. 输出高活性模型训练汇总、高活性参数推荐表和稳定性参数范围表；
6. 建立可复现运行流程，删除 `results/` 后仍可重新生成结果。

本阶段基于两批真实文献提取数据，完成了 AuNC 高活性和高分散稳定性方向的初步 QSPR 分析。高活性部分以 Km、Vmax 等 TMB/POD 动力学指标作为性能标签，进行小样本 Ridge 回归；高分散性 / 稳定性部分由于 retention 类标签仍有限，采用文献描述符范围总结的方式输出参数建议。结果用于指导后续实验优先级，不作为最终定量结论。
