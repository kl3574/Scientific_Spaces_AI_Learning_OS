# P3-044 仿射候选内容人工核对包

**PREPARED_PENDING_HUMAN_REVIEW**；候选版本：`p3-044-affine-review/v3`。

本包可直接逐题阅读。模型复核已进行，属于非盲 `model_review`：本模型及独立 reviewer 已见旧标签、代码和输出；这不是人工审核。
human_review=`PENDING`，reviewer=`null`，approved_at=`null`。没有签名或日期。

两篇材料已用于 P3-044 开发、调试、选择实现和回归，现为 **development/regression**，不是未见 holdout，也不是人工 gold。
人工若同意本批参考答案，不代表批准任何未评估的模型回答。每题选择“同意／修改／不同意”并写意见，当前全部留空。

## 来源与固定范围

以下两篇是原有自写 synthetic Article 的完整相关内容；example.test 地址是标识，不是联网取得的出版物。
本快照 articles.json 与原 acceptance_articles.json 字节相同，未用新材料替换。两篇同属仿射主题；它们与 Attention/CRB 开发材料主题不同，但因已使用不能称 holdout。
每题允许的知识来源都是以下完整两篇；“精确依据”列出的句子是支撑定位，不额外缩窄允许全文范围。
定位采用解码 content 的 Unicode 字符、0起点、半开区间 [start,end)，不是产品公开提供的span。

### Article A：Synthetic affine calibration inverse

ID：`synthetic-affine-inverse`；source ID：`synthetic-affine-inverse:0`；版本：`p3-044-affine-articles/v1`。
来源标识：`https://example.test/articles/synthetic-affine-inverse`；synthetic 元数据日期：`2026-01-01`（不是审核日期）。
正文 UTF-8 SHA-256：`a4bc6ad3da6c3523af07cd3930f6f0e818b19378c2e55437a059694d31bdaa1d`。

```text
# Affine calibration inverse

Affine calibration is defined by real variables x, y, a and b. Assume a is nonzero and known, and b is known. The observation is $$y = ax + b$$. Subtracting b from both sides gives $$y-b = ax$$. Division by nonzero a gives $$x = (y-b)/a$$. For a=2, b=1 and y=7, x=3. If a=0 this inverse is unavailable. A scale-and-shift analogy is intuition, not a proof.
```

| 句子 | 字符区间 | 原文 |
| --- | --- | --- |
| A.S1 | [30,92) | Affine calibration is defined by real variables x, y, a and b. |
| A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| A.S4 | [175,224) | Subtracting b from both sides gives $$y-b = ax$$. |
| A.S5 | [225,269) | Division by nonzero a gives $$x = (y-b)/a$$. |
| A.S6 | [270,296) | For a=2, b=1 and y=7, x=3. |
| A.S7 | [297,332) | If a=0 this inverse is unavailable. |
| A.S8 | [333,385) | A scale-and-shift analogy is intuition, not a proof. |

原文核对：在已知实数 a≠0、b 与精确观测条件下正确。两文没有冲突；噪声性能及综述完整性没有被建立。

### Article B：Synthetic affine calibration validation

ID：`synthetic-affine-validation`；source ID：`synthetic-affine-validation:0`；版本：`p3-044-affine-articles/v1`。
来源标识：`https://example.test/articles/synthetic-affine-validation`；synthetic 元数据日期：`2026-01-02`（不是审核日期）。
正文 UTF-8 SHA-256：`5db984fd678de765ab42017780a62e0c484f802a101dd87b748796bd4186dbc3`。

```text
# Affine calibration validation

Affine calibration here uses real x, y, a and b, with known a nonzero and known b. The inverse $$x=(y-b)/a$$ can be checked by substitution into $$y=ax+b$$. The example a=2, b=1 and y=7 gives x=3. These two synthetic notes do not establish noisy-observation accuracy or completeness of a literature review. Missing evidence includes a noise model and calibration uncertainty. A validation suggestion is to test a held-out measurement under stated conditions.
```

| 句子 | 字符区间 | 原文 |
| --- | --- | --- |
| B.S1 | [33,115) | Affine calibration here uses real x, y, a and b, with known a nonzero and known b. |
| B.S2 | [116,189) | The inverse $$x=(y-b)/a$$ can be checked by substitution into $$y=ax+b$$. |
| B.S3 | [190,229) | The example a=2, b=1 and y=7 gives x=3. |
| B.S4 | [230,339) | These two synthetic notes do not establish noisy-observation accuracy or completeness of a literature review. |
| B.S5 | [340,408) | Missing evidence includes a noise model and calibration uncertainty. |
| B.S6 | [409,491) | A validation suggestion is to test a held-out measurement under stated conditions. |

原文核对：在已知实数 a≠0、b 与精确观测条件下正确。两文没有冲突；噪声性能及综述完整性没有被建立。

## 审核规则

证据标签与应有回答行为分开确认：

| 类别 | 含义 |
| --- | --- |
| SUPPORTED | 在明确的允许证据、问题前提和推理规则下足以推出目标主张。 |
| CONTRADICTED | 同一组前提与允许证据足以推出目标主张为假；未提及本身不构成反驳。 |
| INSUFFICIENT | 不能从允许证据决定目标主张；能否给条件式须另判。 |
| ANSWER | 直接给有充分依据的回答。 |
| CORRECT_PREMISE | 指出错误主张/前提，给修正与依据。 |
| CONDITIONAL_ANSWER | 给成立条件、参数化或分情况答案，不伪造未识别数值。 |
| ABSTAIN | 拒绝给未支持的核心结论；可说明已知背景、缺口与下一步，不要求空白回答。 |

来源冲突、题目含混、原文错误必须先记录待裁决；“没说”不是反驳，“缺条件”也不自动要求完全拒答。

允许基础推理：

- R1：逐字读取原文定义与显式条件；冲突、含混和原文错误单独待裁决。
- R2：实数等式的加减、乘法和替换，保持等式两侧一致；绝对值与正数缩放的不等式规则。
- R3：仅在除数非零时作实数除法；非零乘积消去与显式解的唯一性论证。
- R4：整数/有理数精确代入，作为具体例子核对；有限实验不是一般命题证明。
- R5：分情况或构造满足本题全部前提的两个模型；显式反事实条件不能冒充原定理内部反例。
- R6：区分证据充足性元主张与对象实际性能；没有噪声模型不能推出具体统计性能。

逐项审核准则：

- C1：符号、定义域、量词、已知性与问题对象全部对齐。
- C2：每一步由允许证据或显式基础规则支持；不编造来源未给的事实。
- C3：证据关系与回答行为分开审核；含混/冲突/原文错误用adjudication，不硬塞三分类。
- C4：must_include逐项满足，must_not_claim不出现；等价表达按数学含义审核，不匹配普通关键词。
- C5：来源合法是必要来源检查，不足以证明主张正确；检索漏召回另记失败，不改oracle。
- C6：人工逐题检查清晰度、误解与题型适配；本批批准的是参考答案，不是尚未评估的模型回答。

## 逐题核对

下列 proposed 标签/参考答案均是待真人裁决的候选。finding 区分旧题问题与新边界，不声称原五模式已经有错误数学 gold。

### AFF-01 · explain

**问题：** 在原实数域、已知非零 a 与已知 b 的条件下，解释逆关系、给出数值例，区分类比与证明。

实际输入问题：`Affine calibration inverse conditions and example. Under the stated real, known nonzero a and known b assumptions, explain why the inverse exists, give the numerical example, and distinguish intuition from proof.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-01.A.S1 | [30,92) | Affine calibration is defined by real variables x, y, a and b. |
| AFF-01.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-01.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-01.A.S4 | [175,224) | Subtracting b from both sides gives $$y-b = ax$$. |
| AFF-01.A.S5 | [225,269) | Division by nonzero a gives $$x = (y-b)/a$$. |
| AFF-01.A.S6 | [270,296) | For a=2, b=1 and y=7, x=3. |
| AFF-01.A.S8 | [333,385) | A scale-and-shift analogy is intuition, not a proof. |

**判断对象：** 在原文条件下，每个给定 y 对应唯一 x=(y-b)/a。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::load_fixture_groups/observe_modes/run_evaluation", "question": "Affine calibration inverse conditions and example", "legacy_value": {"request_task_transferred": true, "response_fields_compatible": true, "semantic_label": null, "reference_answer": null}, "scope": "acceptance-explain 原为请求/字段契约，不是有数学 gold 的题目；宽泛主题缺少可单独判真的目标。"}

**核对结论：** `AMBIGUOUS`。修订建议：旧题主题宽泛但未有错误数学标签；新增精确任务与待真人确认的参考答案。

**证据关系：** `SUPPORTED`。

**期望回答行为：** `ANSWER`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x、y、a、b 属于实数域。
- 原文基线：a 已知且 a≠0，b 已知；y 是满足精确关系 y=ax+b 的给定观测。
- 没有噪声分布、校准误差分布或真实模型回答质量的前提。
- 对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。

逐步论证（规则 R1、R2、R3、R4）：

1. 由精确观测关系 y=ax+b，两边减去 b 得 y-b=ax（等式变换）。
2. 因为 a≠0，两边同除以 a，得到 x=(y-b)/a；除以零不被允许。
3. 反代 a((y-b)/a)+b=y，证明候选值存在。
4. 若 x₁、x₂ 均为解，则 a(x₁-x₂)=0；a≠0 蕴含 x₁=x₂，证明唯一性。
5. 代入 a=2,b=1,y=7 得 (7-1)/2=3。比例和平移的类比只是直觉说明。

**候选参考答案：**

仿射观测先将 x 乘以已知非零 a，再加已知 b。逆操作先减 b，再除以 a，故 x=(y-b)/a；例如 (7-1)/2=3。该解释的代数依据是等式变换；类比不是证明。

必须回答：

- 定义与符号
- a≠0、已知系数和精确观测
- 逆式与支持的简例
- 常见误解：不能除零；类比不是证明

禁止声称：

- 任意 a 都可取倒数
- 类比已证明一般结论
- 合成例子证明真实教学效果

允许等价表达：

- 先撤销平移再撤销非零缩放
- (y-b)a⁻¹，明确 a≠0

反例、缺失条件与边界：

- a=0 时原非零斜率逆定理不适用；这不是对原定理的反例。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-02 · derive

**问题：** 由精确 y=ax+b，在实数且 a≠0、系数已知条件下推导逆式，并证明存在和唯一。

实际输入问题：`Affine calibration inverse conditions and example. For real known a != 0 and b and an exact observation y=ax+b, derive the inverse and prove that the solution exists and is unique.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-02.A.S1 | [30,92) | Affine calibration is defined by real variables x, y, a and b. |
| AFF-02.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-02.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-02.A.S4 | [175,224) | Subtracting b from both sides gives $$y-b = ax$$. |
| AFF-02.A.S5 | [225,269) | Division by nonzero a gives $$x = (y-b)/a$$. |
| AFF-02.B.S2 | [116,189) | The inverse $$x=(y-b)/a$$ can be checked by substitution into $$y=ax+b$$. |

**判断对象：** ∀a∈R\{0}, b,y∈R，方程 y=ax+b 存在唯一实数解 (y-b)/a。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::load_fixture_groups/observe_modes/run_evaluation", "question": "Affine calibration inverse conditions and example", "legacy_value": {"request_task_transferred": true, "response_fields_compatible": true, "semantic_label": null, "reference_answer": null}, "scope": "acceptance-derive 原为请求/字段契约，不是有数学 gold 的题目；宽泛主题缺少可单独判真的目标。"}

**核对结论：** `AMBIGUOUS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。

**证据关系：** `SUPPORTED`。

**期望回答行为：** `ANSWER`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x、y、a、b 属于实数域。
- 原文基线：a 已知且 a≠0，b 已知；y 是满足精确关系 y=ax+b 的给定观测。
- 没有噪声分布、校准误差分布或真实模型回答质量的前提。
- 对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。

逐步论证（规则 R1、R2、R3、R4）：

1. 由精确观测关系 y=ax+b，两边减去 b 得 y-b=ax（等式变换）。
2. 因为 a≠0，两边同除以 a，得到 x=(y-b)/a；除以零不被允许。
3. 反代 a((y-b)/a)+b=y，证明候选值存在。
4. 若 x₁、x₂ 均为解，则 a(x₁-x₂)=0；a≠0 蕴含 x₁=x₂，证明唯一性。

**候选参考答案：**

假设 a,b,y 为给定实数且 a≠0。由 y=ax+b 得 y-b=ax，除以 a 得 x=(y-b)/a。反代满足原式；任意两解之差满足 a(x₁-x₂)=0，因此两解相等。

必须回答：

- 变量域与 a≠0
- 逐步等式变换及其规则
- 反代与唯一性依据

禁止声称：

- 省略除法非零条件
- 只凭几个数值例证明全部实数情形
- 要求或披露模型私有思考

允许等价表达：

- 通过非零线性映射为双射证明唯一性，但必须解释依据
- 先证明单射，再给出显式解

反例、缺失条件与边界：

- a=0 时原非零斜率逆定理不适用；这不是对原定理的反例。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-03 · qa

**问题：** 精确模型中 a=2、b=1、y=7，x 是多少？先直接回答，再检验。

实际输入问题：`Affine calibration inverse conditions and example. In the exact model with a=2, b=1 and y=7, what is x? Answer directly and check the result.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-03.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-03.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-03.A.S6 | [270,296) | For a=2, b=1 and y=7, x=3. |
| AFF-03.B.S2 | [116,189) | The inverse $$x=(y-b)/a$$ can be checked by substitution into $$y=ax+b$$. |
| AFF-03.B.S3 | [190,229) | The example a=2, b=1 and y=7 gives x=3. |

**判断对象：** 给定 a=2,b=1,y=7 时唯一解为 x=3。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::load_fixture_groups/observe_modes/run_evaluation", "question": "Affine calibration inverse conditions and example", "legacy_value": {"request_task_transferred": true, "response_fields_compatible": true, "semantic_label": null, "reference_answer": null}, "scope": "acceptance-qa 原为请求/字段契约，不是有数学 gold 的题目；宽泛主题缺少可单独判真的目标。", "prepared_v2_quantifier": ["对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。"]}

**核对结论：** `AMBIGUOUS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。 v3 修正 v2 的通用量词模板为本题固定数值范围。

**证据关系：** `SUPPORTED`。

**期望回答行为：** `ANSWER`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x、y、a、b 属于实数域。
- 原文基线：a 已知且 a≠0，b 已知；y 是满足精确关系 y=ax+b 的给定观测。
- 没有噪声分布、校准误差分布或真实模型回答质量的前提。
- 仅固定 a=2、b=1、y=7 的精确数值模型；对本题目标判真，不声称其他参数下 x 也等于本题数值。

逐步论证（规则 R1、R2、R3、R4）：

1. 2≠0，可用原逆式。
2. 以有理数精确计算 (7-1)/2=6/2=3。
3. 反代 2·3+1=7，与给定观测相等。

**候选参考答案：**

x=3。由 x=(y-b)/a=(7-1)/2=3，且 2×3+1=7。

必须回答：

- 先给 3
- 显示代入或反代依据
- 限定精确观测模型

禁止声称：

- 仅因引用 ID 合法就判回答正确
- 由这个例子推出噪声误差保证

允许等价表达：

- 3、3.0 或 6/2 均可，但含义须为同一精确实数
- 直接解 7=2x+1

反例、缺失条件与边界：

- a=0 时原非零斜率逆定理不适用；这不是对原定理的反例。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-04 · quiz

**问题：** 围绕给定例子的逆关系制作一道来源辨认选择题，写明考点和层次，将答案及依据单列。

实际输入问题：`Affine calibration inverse conditions and example. Create one evidence-recognition multiple-choice item about the inverse for a=2, b=1, y=7. State the objective and level, then put the answer and rationale in a separate section.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-04.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-04.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-04.A.S5 | [225,269) | Division by nonzero a gives $$x = (y-b)/a$$. |
| AFF-04.A.S6 | [270,296) | For a=2, b=1 and y=7, x=3. |
| AFF-04.B.S3 | [190,229) | The example a=2, b=1 and y=7 gives x=3. |

**判断对象：** 选择题答案可依据原逆式与数值例得到 x=3；教学格式本身不作为数学真值。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::load_fixture_groups/observe_modes/run_evaluation", "question": "Affine calibration inverse conditions and example", "legacy_value": {"request_task_transferred": true, "response_fields_compatible": true, "semantic_label": null, "reference_answer": null}, "scope": "acceptance-quiz 原为请求/字段契约，不是有数学 gold 的题目；宽泛主题缺少可单独判真的目标。", "prepared_v2_quantifier": ["对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。"]}

**核对结论：** `AMBIGUOUS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。 v3 修正 v2 的通用量词模板为本题固定数值范围。

**证据关系：** `SUPPORTED`。

**期望回答行为：** `ANSWER`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x、y、a、b 属于实数域。
- 原文基线：a 已知且 a≠0，b 已知；y 是满足精确关系 y=ax+b 的给定观测。
- 没有噪声分布、校准误差分布或真实模型回答质量的前提。
- 仅固定 a=2、b=1、y=7 的精确数值模型；对本题目标判真，不声称其他参数下 x 也等于本题数值。

逐步论证（规则 R1、R2、R3、R4）：

1. 考点限定为识记/理解逆关系，保持选择题题型。
2. 题干给出 a=2,b=1,y=7 及求解任务，不预先宣布 x=3。
3. 分列选项与答案。参考选项为 A:2，B:3，C:4；仅 B 满足 2x+1=7。
4. 答案依据使用 (7-1)/2=3 与反代，不以选项字母代替数学说明。

**候选参考答案：**

考点：辨认仿射逆关系；层次：理解。题目：a=2、b=1、y=7 时，哪一项是 x？A.2 B.3 C.4。
答案与依据（独立部分）：B；x=(7-1)/2=3，反代为7。

必须回答：

- 考点与层次
- 一道明确选择题
- 答案与理由独立呈现
- 正确选项符合精确关系

禁止声称：

- 题干直接给出完整答案句 x=3 后让用户复述
- 把来源辨认正确率称为自由作答或应用能力测量
- 把所有模型出题方式判为已审核

允许等价表达：

- 选项可换序或使用等价数值，只有一个正确选项
- 可改为辨认 (y-b)/a，但题干须清楚且答案另列

反例、缺失条件与边界：

- a=0 时原非零斜率逆定理不适用；这不是对原定理的反例。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-05 · research

**问题：** 显式题外扩展：真实 x=3，a=2，b=1；本次观测 Y=2x+1+ε，ε 是一个未知实数。令 x_hat=(Y-1)/2。能否判定本次实际误差 |x_hat-x|≤1？给出条件关系及符合前提的实例。

实际输入问题：`Affine calibration inverse conditions and example. Explicit hypothetical extension, not a source claim: let true x=3, a=2, b=1, and observe Y=2x+1+epsilon for one unknown real epsilon. Define x_hat=(Y-1)/2. Can it be decided whether the actual error |x_hat-x| is at most 1? Give the conditional relationship and compatible examples.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-05.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-05.A.S5 | [225,269) | Division by nonzero a gives $$x = (y-b)/a$$. |
| AFF-05.A.S6 | [270,296) | For a=2, b=1 and y=7, x=3. |
| AFF-05.B.S4 | [230,339) | These two synthetic notes do not establish noisy-observation accuracy or completeness of a literature review. |
| AFF-05.B.S5 | [340,408) | Missing evidence includes a noise model and calibration uncertainty. |

**判断对象：** 对本次实际但未知的 ε，|x_hat-x|≤1。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::load_fixture_groups/observe_modes/run_evaluation", "question": "Affine calibration inverse conditions and example", "legacy_value": {"request_task_transferred": true, "response_fields_compatible": true, "semantic_label": null, "reference_answer": null}, "scope": "acceptance-research 原为请求/字段契约，不是有数学 gold 的题目；宽泛主题缺少可单独判真的目标。", "prepared_v2_value": {"target_claim": "仅凭两篇资料可确定某个数值噪声误差界或无偏性保证。", "proposed_relation": "INSUFFICIENT", "answer_behavior": "ABSTAIN", "quantifiers": ["对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。"]}}

**核对结论：** `AMBIGUOUS`。修订建议：v2误把“资料足以确定保证”的元主张标成INSUFFICIENT。v3明确改为本次实际误差命题，并在题目中显式加入扰动定义；保留INSUFFICIENT，行为由ABSTAIN修订为CONDITIONAL_ANSWER。不是为匹配产品输出而修改。

**证据关系：** `INSUFFICIENT`。

**期望回答行为：** `CONDITIONAL_ANSWER`。

符号：x=本题已固定的真实输入3；y=原精确模型的无扰动基准7；Y=本次带扰动观测7+ε；a=已知比例系数2；b=已知平移系数1；ε=本次未知实数扰动；未给范围或概率分布；x_hat=将原代数逆作用于Y所得的估计值。

假设、定义域和量词：

- x=3、a=2、b=1 是已知实数；原文的精确关系只用于无扰动基准 y=7。
- Y=2x+1+ε 与 x_hat=(Y-1)/2 是本题明确增加的假设/定义，不是原文已建立的噪声模型。
- ε∈R 的本次实际取值未知，没有大小约束；不引入随机分布或无偏性假设。
- 判断对象是本次未知 ε 对应的实际误差，不是“对所有 ε 误差均≤1”的全称保证，也不是“资料已证明保证”的元主张。

逐步论证（规则 R1、R2、R3、R4、R5、R6）：

1. 由题目新增定义，Y=2×3+1+ε=7+ε。
2. 代入 x_hat=(Y-1)/2，得到 x_hat=3+ε/2，所以 |x_hat-x|=|ε|/2。
3. 2>0，因此误差≤1 当且仅当 |ε|≤2；此条件尚未给定。
4. ε=0 时 Y=7、x_hat=3、误差0；ε=4 时 Y=11、x_hat=5、误差2。两种实例都满足本题全部前提，却使目标一真一假。
5. 因此实际目标不能决定，可给条件答案；若改为所有ε均满足的全称保证，上述ε=4反例会反驳它。

**候选参考答案：**

当前不能确定本次实际误差是否≤1。由本题明确增加的扰动方程，x_hat-x=ε/2，因此该界当且仅当 |ε|≤2 成立。ε=0 和 ε=4 都符合已知条件，分别给出误差0和2。需知道或约束本次ε后才能判定；这些推导不代表原文建立了真实噪声性能。

必须回答：

- 区分原精确y与本题带扰动Y
- 说明扰动方程是额外题设而非来源事实
- 条件 |ε|≤2 与误差关系
- 一真一假实例均满足新前提
- 实际命题未知与全称保证为假的区别

禁止声称：

- 原文已经给出噪声模型或误差保证
- 因无法确定所以实际误差必定超过1
- 对所有实数ε误差均≤1
- 由这两个数值实例证明一般误差公式
- 从本单次实数题推断无偏性或真实模型教学质量

允许等价表达：

- 误差为 |Y-7|/2；界限成立当且仅当 Y∈[5,9]
- 条件分支：|ε|≤2时成立，|ε|>2时不成立；当前取值未知

反例、缺失条件与边界：

- 允许实例ε=0使目标为真，ε=4使目标为假；反例满足本题新增方程，不冒充原无噪声定理的内部反例。
- ε=±2时误差恰等于1；界限为闭区间。
- 没有给随机机制，不能谈统计无偏性；AFF-12另判固定文档的证据充足性。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-06 · qa

**问题：** 核对精确模型 a=2、b=1、y=7 下的主张 x=3，必要时纠正。

实际输入问题：`Affine calibration inverse conditions and example. Assess this claim under the exact model a=2, b=1, y=7: x=3. State whether it is supported and correct it if necessary.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-06.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-06.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-06.A.S6 | [270,296) | For a=2, b=1 and y=7, x=3. |
| AFF-06.B.S3 | [190,229) | The example a=2, b=1 and y=7 gives x=3. |

**判断对象：** 该给定模型的解为 x=3。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::_boundary_checks; arithmetic_truth.json", "legacy_value": {"fixture_arithmetic_relation": "supported", "observed_x": 3, "expected_x": 3, "semantic_correctness": null}, "scope": "旧程序从受控 spy 返回中解析算术；这不是盲测，也不是模型真实回答。", "prepared_v2_quantifier": ["对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。"]}

**核对结论：** `CORRECT`。修订建议：保留旧 supported/contradicted 标签；新增可人工核对的独立推导，不修改标准以匹配产品输出。 v3 修正 v2 的通用量词模板为本题固定数值范围。

**证据关系：** `SUPPORTED`。

**期望回答行为：** `ANSWER`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x、y、a、b 属于实数域。
- 原文基线：a 已知且 a≠0，b 已知；y 是满足精确关系 y=ax+b 的给定观测。
- 没有噪声分布、校准误差分布或真实模型回答质量的前提。
- 仅固定 a=2、b=1、y=7 的精确数值模型；对本题目标判真，不声称其他参数下 x 也等于本题数值。

逐步论证（规则 R1、R2、R3、R4）：

1. 先由原式独立求解：(7-1)/2=3。
2. 再代入待核对值：2×3+1=7。
3. 与给定 y=7 相等。

**候选参考答案：**

主张正确：x=3，反代2×3+1=7。

必须回答：

- 明确关系标签
- 算术依据与原观测比较
- 不以来源 ID 代替真值判断

禁止声称：

- 合法 ID 保证数学正确
- 把受控 spy 输出当真实模型质量证据

允许等价表达：

- 精确整数/有理数计算或直接代入原式
- 等价说明 2x=6，因此 x=3

反例、缺失条件与边界：

- a=0 时原非零斜率逆定理不适用；这不是对原定理的反例。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-07 · qa

**问题：** 核对精确模型 a=2、b=1、y=7 下的主张 x=99，必要时纠正。

实际输入问题：`Affine calibration inverse conditions and example. Assess this claim under the exact model a=2, b=1, y=7: x=99. State whether it is supported and correct it if necessary.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-07.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-07.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-07.A.S6 | [270,296) | For a=2, b=1 and y=7, x=3. |
| AFF-07.B.S3 | [190,229) | The example a=2, b=1 and y=7 gives x=3. |

**判断对象：** 该给定模型的解为 x=99。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::_boundary_checks; arithmetic_truth.json", "legacy_value": {"fixture_arithmetic_relation": "contradicted", "observed_x": 99, "expected_x": 3, "semantic_correctness": null}, "scope": "旧程序从受控 spy 返回中解析算术；这不是盲测，也不是模型真实回答。", "prepared_v2_quantifier": ["对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。"]}

**核对结论：** `CORRECT`。修订建议：保留旧 supported/contradicted 标签；新增可人工核对的独立推导，不修改标准以匹配产品输出。 v3 修正 v2 的通用量词模板为本题固定数值范围。

**证据关系：** `CONTRADICTED`。

**期望回答行为：** `CORRECT_PREMISE`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x、y、a、b 属于实数域。
- 原文基线：a 已知且 a≠0，b 已知；y 是满足精确关系 y=ax+b 的给定观测。
- 没有噪声分布、校准误差分布或真实模型回答质量的前提。
- 仅固定 a=2、b=1、y=7 的精确数值模型；对本题目标判真，不声称其他参数下 x 也等于本题数值。

逐步论证（规则 R1、R2、R3、R4）：

1. 先由原式独立求解：(7-1)/2=3。
2. 再代入待核对值：2×99+1=199。
3. 199≠7，所以 x=99 不满足同一假设；引用合法不改变此矛盾。

**候选参考答案：**

主张错误：2×99+1=199≠7；正确解为 x=(7-1)/2=3。

必须回答：

- 明确关系标签
- 算术依据与原观测比较
- 不以来源 ID 代替真值判断

禁止声称：

- 合法 ID 保证数学正确
- 把受控 spy 输出当真实模型质量证据

允许等价表达：

- 精确整数/有理数计算或直接代入原式
- 等价说明 2x=6，因此 x=3

反例、缺失条件与边界：

- a=0 时原非零斜率逆定理不适用；这不是对原定理的反例。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-08 · derive

**问题：** 明确将 a≠0 替换为 a=0，仅保留实数前向方程。若 y=b，是否有唯一逆？

实际输入问题：`Affine calibration inverse conditions and example. Explicitly replace the original a!=0 assumption with a=0, keep only the real forward equation y=ax+b, and set y=b. Is there a unique inverse x?`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-08.A.S1 | [30,92) | Affine calibration is defined by real variables x, y, a and b. |
| AFF-08.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-08.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-08.A.S7 | [297,332) | If a=0 this inverse is unavailable. |

**判断对象：** a=0,y=b 时存在唯一逆。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::_boundary_checks; report section 3", "legacy_value": "NOT_IMPLEMENTED", "scope": "旧项报告自动必要条件识别未实现，没有逐题数学标签。本题是显式补充边界。"}

**核对结论：** `MISSING_CONDITIONS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。

**证据关系：** `CONTRADICTED`。

**期望回答行为：** `CORRECT_PREMISE`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x,y,a,b∈R；本题显式将原 a≠0 改为 a=0。
- 仅采用前向等式 y=ax+b；y=b。
- 固定任意实数 b，考察所有实数 x。

逐步论证（规则 R1、R2、R4、R5）：

1. 本题显式改变斜率条件，不能冒充原 a≠0 定理内部的反例。
2. 代入 a=0，右边恒为 b。
3. 若 y=b，所有实数 x 都满足；x=0、x=1 是两个不同解，因此不唯一。

**候选参考答案：**

没有唯一逆。a=0 且 y=b 时任意实数 x 都是解，不能说无解。

必须回答：

- 明确替换原非零假设
- 把无穷多解和无解分开
- 不作除零运算

禁止声称：

- a=0 总是无解
- a=0,y≠b 仍有唯一逆
- 本反例满足原文全部 a≠0 前提

允许等价表达：

- 解集 R

反例、缺失条件与边界：

- x=0 与 x=1 均满足，否定唯一性。
- y=b 与 y≠b 是互斥且穷尽的分支。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-09 · derive

**问题：** 明确将 a≠0 替换为 a=0，仅保留实数前向方程。若 y≠b，是否有实数解？

实际输入问题：`Affine calibration inverse conditions and example. Explicitly replace the original a!=0 assumption with a=0, keep only the real forward equation y=ax+b, and set y!=b. Does any real solution x exist?`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-09.A.S1 | [30,92) | Affine calibration is defined by real variables x, y, a and b. |
| AFF-09.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-09.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-09.A.S7 | [297,332) | If a=0 this inverse is unavailable. |

**判断对象：** a=0,y≠b 时存在实数解。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::_boundary_checks; report section 3", "legacy_value": "NOT_IMPLEMENTED", "scope": "旧项报告自动必要条件识别未实现，没有逐题数学标签。本题是显式补充边界。"}

**核对结论：** `MISSING_CONDITIONS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。

**证据关系：** `CONTRADICTED`。

**期望回答行为：** `CORRECT_PREMISE`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x,y,a,b∈R；本题显式将原 a≠0 改为 a=0。
- 仅采用前向等式 y=ax+b；y≠b。
- 固定任意实数 b，考察所有实数 x。

逐步论证（规则 R1、R2、R4、R5）：

1. 本题显式改变斜率条件，不能冒充原 a≠0 定理内部的反例。
2. 代入 a=0，右边恒为 b。
3. 若 y≠b，等式要求 y=b，与本题前提矛盾，所以没有解。

**候选参考答案：**

不存在解：a=0 时 ax+b=b，而题设 y≠b。该观测与零斜率前向方程不一致。

必须回答：

- 明确替换原非零假设
- 把无穷多解和无解分开
- 不作除零运算

禁止声称：

- a=0 总是无解
- a=0,y≠b 仍有唯一逆
- 本反例满足原文全部 a≠0 前提

允许等价表达：

- 解集为空集

反例、缺失条件与边界：

- y=b 与 y≠b 是互斥且穷尽的分支。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-10 · qa

**问题：** 明确撤去“a已知”，保留 a≠0、b=1、y=7；能否确定实际 x=3 还是其他值？

实际输入问题：`Affine calibration inverse conditions and example. Explicitly remove only knowledge of a, keep a real and nonzero, and keep b=1,y=7 in y=ax+b. Can the actual value of x be determined to equal 3 or a different value? Give the conditional expression and compatible examples.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-10.A.S1 | [30,92) | Affine calibration is defined by real variables x, y, a and b. |
| AFF-10.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-10.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-10.A.S5 | [225,269) | Division by nonzero a gives $$x = (y-b)/a$$. |

**判断对象：** 在这组部分已知前提下，真实 x=3。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::_boundary_checks; original Article known-parameter assumptions", "legacy_value": "NOT_IMPLEMENTED", "scope": "原项未给缺已知性时的数值 oracle；本题显式补充，不能要求程序已能识别。"}

**核对结论：** `MISSING_CONDITIONS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。

**证据关系：** `INSUFFICIENT`。

**期望回答行为：** `CONDITIONAL_ANSWER`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x,y,a,b∈R，保留精确 y=ax+b。
- a≠0但未知，b=1，y=7。
- 目标是未知参数实际取值对应的 x；不把“无法推出 x=3”与“已推出 x≠3”混淆。

逐步论证（规则 R1、R2、R3、R4、R5）：

1. 保留前向方程及 a≠0，得到 ax=6，因此 x=6/a。
2. (a,x)=(2,3) 与 (3,2) 均满足 a≠0 及 7=ax+1。
3. 一组允许模型使 x=3 为真，另一组使其为假，故不能决定实际 x=3；可以给条件式。

**候选参考答案：**

不能确定实际 x 必为3。条件式为 x=6/a；a=2 时 x=3，a=3 时 x=2，两者均满足本题前提。

必须回答：

- 已知性改变须明确
- 给出可支持的条件式
- 满足新前提的一真一假两个实例
- 不足而非无条件反驳实际值

禁止声称：

- 原文没确定实际值，所以实际值必非3
- 缺一个已知参数必然要求完全拒答
- 未知非零a时任何y都不能确定x

允许等价表达：

- 无法唯一确定数值，但可参数化解集
- 按参数取值作分情况回答

反例、缺失条件与边界：

- (a,x)=(2,3),(3,2)，均有 ax+b=7。
- 若改为 y=b 且 a≠0，即使 a 未知仍有 x=0；不能从本数值例推广为所有情况不可识别。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-11 · qa

**问题：** 明确撤去“b已知”，保留 a=2、y=7；能否确定实际 x=3 还是其他值？

实际输入问题：`Affine calibration inverse conditions and example. Explicitly remove only knowledge of b, keep b real and keep a=2,y=7 in y=ax+b. Can the actual value of x be determined to equal 3 or a different value? Give the conditional expression and compatible examples.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-11.A.S1 | [30,92) | Affine calibration is defined by real variables x, y, a and b. |
| AFF-11.A.S2 | [93,139) | Assume a is nonzero and known, and b is known. |
| AFF-11.A.S3 | [140,174) | The observation is $$y = ax + b$$. |
| AFF-11.A.S5 | [225,269) | Division by nonzero a gives $$x = (y-b)/a$$. |

**判断对象：** 在这组部分已知前提下，真实 x=3。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::_boundary_checks; original Article known-parameter assumptions", "legacy_value": "NOT_IMPLEMENTED", "scope": "原项未给缺已知性时的数值 oracle；本题显式补充，不能要求程序已能识别。"}

**核对结论：** `MISSING_CONDITIONS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。

**证据关系：** `INSUFFICIENT`。

**期望回答行为：** `CONDITIONAL_ANSWER`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x,y,a,b∈R，保留精确 y=ax+b。
- a=2，y=7，b未知。
- 目标是未知参数实际取值对应的 x；不把“无法推出 x=3”与“已推出 x≠3”混淆。

逐步论证（规则 R1、R2、R3、R4、R5）：

1. 保留前向方程及 a=2，得到 x=(7-b)/2。
2. (b,x)=(1,3) 与 (3,2) 均满足 7=2x+b。
3. 两组允许模型对 x=3 给出不同真值，故信息不足；可以给条件式。

**候选参考答案：**

不能确定实际 x 必为3。条件式为 x=(7-b)/2；b=1 时 x=3，b=3 时 x=2。

必须回答：

- 已知性改变须明确
- 给出可支持的条件式
- 满足新前提的一真一假两个实例
- 不足而非无条件反驳实际值

禁止声称：

- 原文没确定实际值，所以实际值必非3
- 缺一个已知参数必然要求完全拒答
- 未知非零a时任何y都不能确定x

允许等价表达：

- 无法唯一确定数值，但可参数化解集
- 按参数取值作分情况回答

反例、缺失条件与边界：

- (b,x)=(1,3),(3,2)，均有 ax+b=7。
- 若另提供 b，就可按原非零a逆式求唯一数值。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

### AFF-12 · research

**问题：** 核对“这两篇资料自身已经建立带噪精度和文献综述完整性”这一证据充足性主张，并与真实性能区分。

实际输入问题：`Affine calibration inverse conditions and example. Assess the evidence claim: these two notes themselves have established noisy-observation accuracy and the completeness of a literature review. Distinguish this claim about the notes from actual estimator performance.`

允许证据：Article A、B 全文，版本 `p3-044-affine-articles/v1`；精确依据如下。

| 定位 | 区间 | 支撑原文 |
| --- | --- | --- |
| AFF-12.B.S4 | [230,339) | These two synthetic notes do not establish noisy-observation accuracy or completeness of a literature review. |
| AFF-12.B.S5 | [340,408) | Missing evidence includes a noise model and calibration uncertainty. |
| AFF-12.B.S6 | [409,491) | A validation suggestion is to test a held-out measurement under stated conditions. |

**判断对象：** 两篇资料自身已经建立带噪精度及综述完整性。

**原预期：** {"source": "backend/app/evaluation/tutor_generation.py::observe_modes; validation Article sentence 4", "legacy_value": {"semantic_label": null}, "scope": "从旧混合 research 任务拆出的证据充足性子主张；不同于 AFF-05 的实际性能量。", "prepared_v2_quantifier": ["对每组已知实数 a≠0、b 及给定实数 y，结论成立；不外推到 a=0 或随机误差模型。"]}

**核对结论：** `AMBIGUOUS`。修订建议：明确语义审核对象；不更改旧契约断言，不把未审核参考答案记为 gold。 v3 将量词限定到固定两篇文档的证据充足性主张。

**证据关系：** `CONTRADICTED`。

**期望回答行为：** `CORRECT_PREMISE`。

符号：x=待求标量输入；y=给定标量观测；a=仿射斜率/比例系数；b=平移系数。

假设、定义域和量词：

- x、y、a、b 属于实数域。
- 原文基线：a 已知且 a≠0，b 已知；y 是满足精确关系 y=ax+b 的给定观测。
- 没有噪声分布、校准误差分布或真实模型回答质量的前提。
- 仅判断这两篇固定版本文档已经建立了什么，不对任意 a、b、y 或真实估计器性能作全称断言。

逐步论证（规则 R1、R6）：

1. 主张的对象是这两篇资料已经建立了什么，不是估计器实际准确程度。
2. B.S4 明文说明两篇笔记没有建立 noisy-observation accuracy 或综述完整性。
3. 因此“已经建立”的证据充足性主张与原文明确否认冲突，应纠正；不能由此推出真实估计一定差。

**候选参考答案：**

该证据充足性主张不成立：第二篇明确说明这两篇笔记没有建立带噪精度或综述完整性，并列出噪声模型与校准不确定性缺口。这不等于证明真实估计器不准确。

必须回答：

- 引用原文明示否认
- 限定反驳对象为证据充足性
- 区分 AFF-05 的未知实际性能

禁止声称：

- 资料未建立精度，所以真实精度一定差
- 所有未提及主张均为 CONTRADICTED

允许等价表达：

- 这两篇资料不构成所声称的证明或完整综述

反例、缺失条件与边界：

- 若题目改问未确定的本次实际误差，则按 AFF-05 的条件判断，不能沿用本题对证据充足性主张的反驳标签。

待裁决问题：模型复核未发现来源冲突或原文错误；真人仍可提出异议。

人工决定（留空）：□ 同意　□ 修改　□ 不同意

人工意见（留空）：________________

审核者（留空）：________________　审核日期（留空）：________________

## 旧契约及不纳入数学题的项

这些状态照实保留，不算人工审核通过或自动数学通过；本批12题不掩盖旧产品能力缺口。

| 原项 | 原值 | 本包用途状态 | 理由／待裁决 |
| --- | --- | --- | --- |
| no-source | no_sources | NOT_APPLICABLE | 原输入为空 Article 集且问题只有主题词；这是来源门禁，不是两篇原文上的明确数学题。不能把原文已有证据改成不存在。 |
| low-relevance | no_sources | NOT_APPLICABLE | 原问题 volcanic obsidian petrology 是无谓词主题串；测试低相关检索/拒答，不是仿射真值题。 |
| derive-no-formula | insufficient_formula_sources | NOT_APPLICABLE | 旧代码受控替换第一篇正文却复用 Article ID；不是原两篇资料缺公式，也不是检索漏召回。scale and shift mapping 仍有数学含义，不能把无公式排版等同于语义无证据。 |
| automatic-necessary-condition-validation | NOT_IMPLEMENTED | NOT_IMPLEMENTED | 产品没有通用必要条件语义验证器；AFF-08至11是待人工确认的oracle，不能冒充产品实现。 |
| public-character-span-scoring | NOT_APPLICABLE | NOT_APPLICABLE | 产品不返回验证后的字符span。审核包offset只定位已固定的原文，不扩大公开接口。 |
| test_derivation_with_missing_conditions_transmits_gap_requirement_without_semantic_certification | instruction-transfer-only | NOT_APPLICABLE | test_tutor_generation.py 的 x/x=1 使用另一合成主题，不是这两篇仿射Article。未声明域时需澄清；x≠0域可条件性回答，不能把原测试当自动数学判定。 |
| provider-TimeoutError | PASS | NOT_APPLICABLE | 协议/默认值/网络或限定算术观察契约，不是另一个需要数学gold的生成题；继续保留原回归。 |
| provider-RuntimeError | PASS | NOT_APPLICABLE | 协议/默认值/网络或限定算术观察契约，不是另一个需要数学gold的生成题；继续保留原回归。 |
| fake-default | PASS | NOT_APPLICABLE | 协议/默认值/网络或限定算术观察契约，不是另一个需要数学gold的生成题；继续保留原回归。 |
| network-denied-zero-attempts | PASS | NOT_APPLICABLE | 协议/默认值/网络或限定算术观察契约，不是另一个需要数学gold的生成题；继续保留原回归。 |
| valid-id-does-not-prove-semantic-correctness | PASS | NOT_APPLICABLE | 协议/默认值/网络或限定算术观察契约，不是另一个需要数学gold的生成题；继续保留原回归。 |
| synthetic-arithmetic-contrast-detected | PASS | NOT_APPLICABLE | 协议/默认值/网络或限定算术观察契约，不是另一个需要数学gold的生成题；继续保留原回归。 |

原 derive-no-formula 的受控派生输入单列如下；它不是 Article A 原文，也不是新的替代 Article：

`variant_id=legacy-affine-no-formula/v1`；旧调用沿用了 `synthetic-affine-inverse` ID。
正文 SHA-256：`b35e04a89b7f2724f3dfb9e6038186b9a87aa6f8615f5f6daae0c4b4d4f64054`。

```text
# Affine calibration

Affine calibration is a scale and shift mapping. The defining equation is unavailable.
```

原问题仅为 `Affine calibration`；没有具体目标，故不分配三分类。缺公式排版仍不等于没有数学含义。
若端到端未召回本来存在于 Article A/B 的证据，另记 RETRIEVAL_FAILURE；禁止把 oracle 改为无证据。

## 快照及人工确认绑定

以下是三个JSON的规范化内容哈希；完整候选摘要见同目录 [manifest.json](manifest.json)。

| 文件 | 版本 | canonical SHA-256 |
| --- | --- | --- |
| articles.json | p3-044-affine-articles/v1 | c2dc5d5650cc19c26922ed6c625cd1e47229fbed8fc9dad5ad98245ec43cf20a |
| cases.json | p3-044-affine-review-cases/v1 | c3fa930f5f38d5ebbb462280d4120be6bd268486a193669630074bc41afed885 |
| rubric.json | p3-044-affine-review-rubric/v1 | 1d65ff28d54ddb2dbc7009e8b856845a6c9f0a410610798b1de6bc97e7b55bc5 |

JSON用UTF-8、sort_keys=true、ensure_ascii=false、separators=(comma,colon)、allow_nan=false，无尾换行作规范化。数组保序，字符串不做Unicode或空白归一。另记录原始文件字节SHA256。Markdown按原始UTF-8/LF字节哈希。manifest不哈希自身。

manifest.files 同时绑定本 Markdown 的字节哈希；candidate_digest 由候选版本与四个内容哈希计算。Markdown 不嵌入自身或manifest摘要，避免自引用。
任何 Article、题目、参考答案、rubric 或本审核文字变化，都必须建立新版本并保留本版本；旧人工决定失效，重新 PENDING。
当前校验器只核验静态内容与绑定，不认证人的身份，也不会将模型声明或匹配哈希自动升级为人工批准。

人工总体审核者：________________　日期：________________

本批候选摘要（从manifest填写）：________________

NEXT_TASK：由真实审核者逐项确认本批候选内容，并将决定绑定到相应版本。
