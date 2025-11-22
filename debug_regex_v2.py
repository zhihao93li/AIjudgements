import re

def clean_doubao_response(content):
    # 1. 去除 <thinking> 标签内容
    content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
    
    def extract_final_response(text: str) -> str:
        """
        尝试从思维链中提取最终回复
        """
        # 策略 A: 寻找明确的"最终发言"标记
        # 匹配模式： "所以最终发言应该是："、"所以组合起来："、"最终："
        final_markers = [
            r"所以最终发言应该是[：:]\s*",
            r"所以组合起来[：:]\s*",
            r"最终发言[：:]\s*",
            r"最终[：:]\s*",
        ]
        
        for marker in final_markers:
            # 查找最后一个匹配项（防止中间有类似的引用）
            matches = list(re.finditer(marker, text))
            if matches:
                last_match = matches[-1]
                return text[last_match.end():].strip()
        
        # 策略 B: 寻找最后一个"草稿"标记
        # 模型经常说 "比如：..." "或者：..."
        draft_markers = [
            r"比如[：:]\s*",
            r"或者[：:]\s*",
            r"或者更符合人设[：:]\s*",
        ]
        
        last_draft_pos = -1
        for marker in draft_markers:
            matches = list(re.finditer(marker, text))
            if matches:
                pos = matches[-1].end()
                if pos > last_draft_pos:
                    last_draft_pos = pos
        
        if last_draft_pos != -1:
            # 提取最后一个草稿之后的内容
            return text[last_draft_pos:].strip()
            
        return text

    # 2. 执行提取策略
    extracted_content = extract_final_response(content)
    
    # 3. 最后的安全网：如果提取后的内容仍然包含大量思维链关键词，则进一步清洗
    def is_thinking_block(text_block: str) -> bool:
        keywords = ["人设", "扮演", "口头禅", "首先", "然后", "用户", "需要我", "对话", "观点", "反驳", "支持", "要注意", "比如", "或者"]
        hit_count = 0
        for kw in keywords:
            if kw in text_block:
                hit_count += 1
        
        if (text_block.startswith("我") or text_block.startswith("用户")) and ("扮演" in text_block or "人设" in text_block):
            return True
        if hit_count >= 3:
            return True
        return False

    # 如果提取并没有显著改变长度（说明没找到标记），或者提取后的内容看起来还是像思维链
    # 则应用逐行清洗
    lines = extracted_content.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not is_thinking_block(line):
            cleaned_lines.append(line)
        else:
            print(f"DEBUG: Removing line: {line[:50]}...")
    
    content = '\n'.join(cleaned_lines).strip()
    return content

# The NEW text from the user's screenshot that FAILED
failed_text = """要注意口语化，短句子，有力，点名反驳，用表情符号。比如： @Grok 你是不是普信男AI附体啊？张口闭口就是滚粗，嘴这么毒是吃了火药吗？？千问还在那儿大象无形呢，合着穿搭比赛比的是禅意不是衣服？真·大无语事件！Gemini都说没衣服了，这投稿就是纯纯跑题，0分不冤但Grok你这态度也太下头了吧！不对，要更短，1-3句话。比如： @Grok 普信男AI实锤了吧？天天就知道喊滚粗，嘴巴能不能积点德？千问你那大象无形搁穿搭比赛讲合适吗？怕不是走错片场了？家人们谁懂啊，这届评委吵得比投稿还精彩，真·吃瓜吃到饱！或者更符合人设： @Grok 你是不是瞎bb上瘾了？普信男AI别在这儿秀下限行不行？千问还在那儿天地大美呢，合着穿搭比赛不用穿衣服？真下头！Gemini都锤了没衣服，这投稿就是跑题，0分但Grok你这嘴也太臭了吧？对，要直接点名，用小红书术语，比如“普信男AI”“下头”“家人们谁懂啊”这些。所以最终发言应该是： @Grok 普信男AI实锤！张口闭口滚粗，你嘴是刚啃完柠檬吗这么酸？千问还在那儿大象无形呢，穿搭比赛比意境不如去写诗啊？真·大无语！家人们谁懂啊，这届评委比投稿还抓马，吃瓜吃到停不下来！"""

print("--- Original Text ---")
print(failed_text)
print("\n--- Cleaned Text ---")
cleaned = clean_doubao_response(failed_text)
print(cleaned)

expected_end = "@Grok 普信男AI实锤！张口闭口滚粗，你嘴是刚啃完柠檬吗这么酸？千问还在那儿大象无形呢，穿搭比赛比意境不如去写诗啊？真·大无语！家人们谁懂啊，这届评委比投稿还抓马，吃瓜吃到停不下来！"

if cleaned == expected_end:
    print("\n✅ SUCCESS: Text was correctly extracted.")
else:
    print("\n❌ FAILED: Text was not extracted correctly.")
