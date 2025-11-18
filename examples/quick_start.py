"""快速开始示例"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.judges import score_image_with_all_judges, run_debate_for_entry
from loguru import logger


async def main():
    """快速开始示例"""
    
    logger.info("🎭 AI 评委系统 - 快速开始示例")
    logger.info("=" * 60)
    
    # 配置你的测试图片
    image_url = "https://picsum.photos/800/600"  # 替换为真实图片 URL
    entry_id = "demo_001"
    competition_type = "outfit"  # 或 "funny"
    
    # ============ 阶段一：评分 ============
    logger.info("\n📊 阶段一：多评委并发评分")
    logger.info("-" * 60)
    
    stage_one_result = await score_image_with_all_judges(
        image_url=image_url,
        entry_id=entry_id,
        competition_type=competition_type,
        extra_text="这是一套日常通勤穿搭",
    )
    
    # 显示评分结果
    logger.info("\n🏆 评分排行榜：")
    for idx, result in enumerate(stage_one_result["sorted_results"], 1):
        logger.info(
            f"  {idx}. {result['judge_display_name']}: "
            f"{result['overall_score']} 分"
        )
        if result.get("one_liner"):
            logger.info(f"     💬 {result['one_liner']}")
    
    # ============ 阶段二：讨论 ============
    logger.info("\n💬 阶段二：评委群聊讨论")
    logger.info("-" * 60)
    
    stage_two_result = await run_debate_for_entry(
        entry_id=entry_id,
        competition_type=competition_type,
        judge_results=stage_one_result["sorted_results"],
    )
    
    # 显示讨论内容
    logger.info("\n🗣️ 群聊记录：")
    for idx, msg in enumerate(stage_two_result.get("messages", []), 1):
        speaker = msg["speaker"].replace("_judge", "")
        content = msg["content"]
        logger.info(f"  [{idx}] {speaker}: {content}")
    
    logger.success("\n✅ 示例运行完成！")


if __name__ == "__main__":
    asyncio.run(main())

