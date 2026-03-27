import requests
import json
from flask import current_app

class LLMService:
    """
    处理大语言模型 (LLM) 接口调用的服务类。
    支持华为云 ModelArts MaaS 平台代理的 DeepSeek 模型。
    """

    def __init__(self):
        self.endpoint = current_app.config['MAAS_ENDPOINT']
        self.api_key = current_app.config['MAAS_API_KEY']
        self.model = current_app.config['MAAS_MODEL']

    def generate_response(self, prompt, system_message="你是一个专业的化学实验专家和数据分析师。"):
        """
        向 LLM 发起请求并获取响应。
        
        Args:
            prompt: 用户输入的提示词
            system_message: 系统预设角色信息
            
        Returns:
            str: 模型生成的文本内容
        """
        if not self.api_key:
            return "Error: API Key is not configured."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }

        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"LLM API Call Failed: {str(e)}")
            return f"Error: 无法获取 AI 建议 ({str(e)})"
        except (KeyError, IndexError) as e:
            current_app.logger.error(f"LLM Response Parsing Failed: {str(e)}")
            return "Error: 解析 AI 响应失败"

    def generate_optimization_advice(self, sample_info, success_prob, top_features):
        """
        基于实验数据生成专业的优化建议。
        """
        feature_desc = "\n".join([
            f"- {f['display_name']}: 当前值 {f['formatted_value']}, SHAP贡献 {f['contribution']:.4f} ({'正向促成' if f['contribution'] > 0 else '负向抑制'})"
            for f in top_features
        ])

        prompt = f"""
请基于以下化学实验数据，作为专家给出专业的优化策略：

【实验背景】
- 样本编号：{sample_info.get('sample_id')}
- 实验轮次：第 {sample_info.get('experiment_round')} 轮
- 实验分组：{sample_info.get('experiment_group')}

【预测分析】
- 优质结果成功率预测值：{success_prob * 100:.1f}%

【关键影响因子 (SHAP)】
{feature_desc}

【要求】
1. 语言自然、专业，以专家语气陈述。
2. 给出 3-4 条具体的实验参数调整建议。
3. 指出下一轮实验应重点关注的变量。
4. 字数控制在 250 字以内，采用 Markdown 列表格式。
"""
        return self.generate_response(prompt)

