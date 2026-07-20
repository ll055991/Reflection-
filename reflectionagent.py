from hellogent.第一部分.第二章.ReflectionAgent.Reflection_Prompt import REFLECT_PROMPT_TEMPLATE
from hellogent.第一部分.第二章.ReflectionAgent.Execution_Prompt import INITIAL_PROMPT_TEMPLATE
from hellogent.第一部分.第二章.ReflectionAgent.Refinement_Prompt import REFINE_PROMPT_TEMPLATE
from hellogent.第一部分.第二章.ReflectionAgent.memory import Memory
from hellogent.第一部分.第二章.ReflectionAgent.llm_client import HelloAgentsLLM
from hellogent.第一部分.第二章.ReflectionAgent.SmartTerminationController.SmartTerminationController import \
    SmartTerminationController


class ReflectionAgent:
    def __init__(self, llm_client, max_iterations=3):
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations

        # 1. 【核心新增】实例化我们的智能终止控制器！
        self.termination_controller = SmartTerminationController(diff_threshold=0.95)

    def run(self, task: str):
        print(f"\n--- 开始处理任务 ---\n任务: {task}")

        # --- 1. 初始执行 ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = INITIAL_PROMPT_TEMPLATE.format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        self.memory.add_record("execution", initial_code)

        # --- 2. 迭代循环: 反思与优化 ---
        for i in range(self.max_iterations):
            current_round = i + 1
            print(f"\n--- 第 {current_round}/{self.max_iterations} 轮迭代 ---")

            # a. 获取上一轮的代码
            last_code = self.memory.get_last_execution()

            # b. 反思
            print("\n-> 正在进行反思...")
            reflect_prompt = REFLECT_PROMPT_TEMPLATE.format(task=task, code=last_code)
            feedback = self._get_llm_response(reflect_prompt)
            self.memory.add_record("reflection", feedback)

            # c. 优化（先生成新代码，才能交给智能控制器做对比评估）
            print("\n-> 正在进行优化...")
            refine_prompt = REFINE_PROMPT_TEMPLATE.format(
                task=task,
                last_code_attempt=last_code,
                feedback=feedback
            )
            refined_code = self._get_llm_response(refine_prompt)

            # d. 【核心重构】使用 SmartTerminationController 替代原本单一的 "无需改进" 判断
            # 我们需要拿到倒数第二版代码作为对比对象 (previous_output)
            all_executions = [rec['content'] for rec in self.memory.records if rec['type'] == 'execution']
            prev_code = all_executions[-1] if len(all_executions) > 0 else ""

            should_stop, reason = self.termination_controller.should_terminate(
                current_step=current_round,
                max_steps=self.max_iterations,
                current_output=refined_code,
                previous_output=prev_code,
                feedback=feedback
            )

            # 把新生成的优化代码正式存入记忆
            self.memory.add_record("execution", refined_code)

            if should_stop:
                print(f"\n🛑 [智能终止触发] 理由: {reason}")
                break
            else:
                print(f"ℹ️ 控制器评估结果: {reason}，将进入下一轮优化。")

        final_code = self.memory.get_last_execution()
        print(f"\n--- 任务完成 ---\n最终生成的代码:\n```python\n{final_code}\n```")
        return final_code

    def _get_llm_response(self, prompt: str) -> str:
        """一个辅助方法，用于调用LLM并获取完整的流式响应。"""
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages=messages) or ""
        return response_text


if __name__ == "__main__":
    llm_client = HelloAgentsLLM()
    reflect = ReflectionAgent(llm_client)
    reflect.run("写一首山水诗")