"""示例测试脚本"""

import asyncio
from app.judges.stage_one import score_image_with_all_judges
from app.judges.stage_two import run_debate_for_entry
from loguru import logger


async def test_stage_one():
    """测试阶段一：评分"""
    logger.info("=" * 60)
    logger.info("测试阶段一：多评委并发评分")
    logger.info("=" * 60)
    
    # 使用测试图片
    test_image_url = "https://picsum.photos/800/600"  # 随机图片（示例）
    
    result = await score_image_with_all_judges(
        image_url=test_image_url,
        entry_id="test_entry_001",
        competition_type="outfit",
        extra_text="这是一个测试用的穿搭图片",
    )
    
    logger.info(f"评分结果: {len(result['judge_results'])} 个评委")
    
    for judge_result in result["sorted_results"]:
        logger.info(
            f"  - {judge_result['judge_display_name']}: "
            f"{judge_result['overall_score']} 分"
        )
    
    return result


async def test_stage_two(judge_results):
    """测试阶段二：讨论"""
    logger.info("=" * 60)
    logger.info("测试阶段二：评委群聊讨论")
    logger.info("=" * 60)
    
    result = await run_debate_for_entry(
        entry_id="test_entry_001",
        competition_type="outfit",
        judge_results=judge_results,
        max_messages=10,
    )
    
    logger.info(f"讨论结果: {len(result.get('messages', []))} 条消息")
    
    for idx, msg in enumerate(result.get("messages", []), 1):
        logger.info(f"  [{idx}] {msg['speaker']}: {msg['content'][:100]}...")
    
    return result


async def main():
    """主测试函数"""
    try:
        # 测试阶段一
        stage_one_result = await test_stage_one()
        
        if not stage_one_result.get("sorted_results"):
            logger.error("阶段一测试失败，跳过阶段二")
            return
        
        # 测试阶段二
        await test_stage_two(stage_one_result["sorted_results"])
        
        logger.success("所有测试完成！")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())

