import hashlib
from difflib import SequenceMatcher
from typing import Tuple, Dict, Any

class SmartTerminationController:
    """
    智能终止控制器：负责多维度评估 Reflection 循环是否应该提前结束。
    """
    def __init__(self, diff_threshold: float = 0.97):
        self.diff_threshold = diff_threshold    # 文本相似度阈值（超过97%认为已无显著修改）
        self.seen_hashes = set()                 # 用于死循环/震荡检测的哈希池

    def should_terminate(
        self,
        current_step: int,
        max_steps: int,
        current_output: str,
        previous_output: str,
        feedback: str
    ) -> Tuple[bool, str]:
        """
        综合判断是否应该终止循环。
        """
        # 1. 保底防线：达到最大步数
        if current_step >= max_steps:
            return True, f"🛑 触及保底防线：达到最大迭代次数 ({max_steps} 步)。"

        # 2. 维一：死循环 / 震荡检测 (Oscillation Check)
        current_hash = hashlib.md5(current_output.encode('utf-8')).hexdigest()
        if current_hash in self.seen_hashes:
            return True, "🔄 检测到死循环（当前代码与历史某一次完全相同），强行终止以节省 Token。"
        self.seen_hashes.add(current_hash)

        # 3. 维二：边际效益检测 (Similarity Check)
        if previous_output:
            similarity = SequenceMatcher(None, previous_output, current_output).ratio()
            if similarity >= self.diff_threshold:
                return True, f"📉 检测到修改边际效应递减（前后代码相似度达 {similarity*100:.1f}%），判定为已收敛。"

        # 4. 维三：传统语义检查 (兼容你原本的“无需改进”)
        if "无需改进" in feedback:
            return True, "✅ 反思认为代码已无需改进，任务完成。"

        return False, "继续迭代"