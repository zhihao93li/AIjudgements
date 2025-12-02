"""
二选一模式的简单测试脚本

使用方法:
python3 test_binary_choice.py

注意：这个测试需要启动服务器后才能运行
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000"

def test_binary_choice_api():
    """测试二选一API"""
    
    print("=" * 80)
    print("测试二选一模式 API")
    print("=" * 80)
    
    # 测试数据
    test_data = {
        "question": "男朋友有没有错？",
        "option_a": "有错",
        "option_b": "没错",
        "text_content": """
        场景：情侣吵架
        
        男朋友说："我觉得你最近太敏感了，什么事都要生气。"
        女朋友说："那是因为你根本不关心我的感受！"
        男朋友说："我怎么不关心了？我每天都在工作赚钱养家！"
        女朋友说："赚钱就是关心吗？你有多久没陪我了？"
        """,
        "extra_context": "这是一个日常生活中常见的情侣争吵场景"
    }
    
    print("\n发送请求...")
    print(f"问题: {test_data['question']}")
    print(f"选项 A: {test_data['option_a']}")
    print(f"选项 B: {test_data['option_b']}")
    print("-" * 80)
    
    # 发送POST请求
    try:
        response = requests.post(
            f"{BASE_URL}/api/binary_choice/judge",
            json=test_data,
            timeout=180  # 3分钟超时
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ 请求成功！")
            print("=" * 80)
            print(f"作品ID: {result['entry_id']}")
            print(f"\n投票结果:")
            print(f"  选择 A ({result['option_a']}): {result['choice_a_count']} 票")
            print(f"  选择 B ({result['option_b']}): {result['choice_b_count']} 票")
            
            print(f"\n评委选择详情:")
            print("=" * 80)
            for judge_result in result['judge_results']:
                print(f"\n【{judge_result['judge_display_name']}】")
                print(f"  选择: {judge_result['choice']} - {judge_result['choice_label']}")
                print(f"  理由: {judge_result['reasoning']}")
                if judge_result.get('inner_monologue'):
                    print(f"  内心独白: {judge_result['inner_monologue'][:100]}...")
            
            if result.get('debate'):
                print(f"\n讨论环节:")
                print("=" * 80)
                debate = result['debate']
                print(f"参与评委: {', '.join(debate['participants'])}")
                print(f"讨论消息数: {len(debate['messages'])}")
                
                print("\n讨论内容:")
                for msg in debate['messages'][:5]:  # 只显示前5条
                    print(f"\n{msg['sequence']}. {msg['speaker']}:")
                    print(f"   {msg['content']}")
                
                if len(debate['messages']) > 5:
                    print(f"\n... 还有 {len(debate['messages']) - 5} 条消息")
            
            print("\n" + "=" * 80)
            print("测试完成！")
            print("=" * 80)
            
            # 保存完整结果到文件
            with open("binary_choice_test_result.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("\n完整结果已保存到: binary_choice_test_result.json")
            
            return result
            
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败！请确保服务器正在运行。")
        print("启动服务器: uvicorn app.main:app --reload")
        return None
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        return None


def test_get_result(entry_id: str):
    """测试获取结果API"""
    
    print("\n" + "=" * 80)
    print(f"测试获取结果 API: entry_id={entry_id}")
    print("=" * 80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/binary_choice/entry/{entry_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ 查询成功！")
            print(f"问题: {result['question']}")
            print(f"投票: A={result['choice_a_count']}, B={result['choice_b_count']}")
            return result
        else:
            print(f"\n❌ 查询失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"\n❌ 查询错误: {e}")
        return None


if __name__ == "__main__":
    # 测试创建二选一评判
    result = test_binary_choice_api()
    
    # 如果成功，测试查询
    if result and result.get('entry_id'):
        import time
        time.sleep(1)
        test_get_result(result['entry_id'])
