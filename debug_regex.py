import re

def clean_doubao_response(content):
    # 1. 去除 <thinking> 标签内容
    content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
    
    # 2. 智能去除思维链 (针对 Doubao 等模型)
    # 策略：如果一段话中包含了大量的"元指令"关键词，则认为是思维链
    
    def is_thinking_block(text_block: str) -> bool:
        # 关键词列表
        keywords = ["人设", "扮演", "口头禅", "首先", "然后", "用户", "需要我", "对话", "观点", "反驳", "支持"]
        hit_count = 0
        for kw in keywords:
            if kw in text_block:
                hit_count += 1
        
        # 强特征：以"我"或"用户"开头，且包含"扮演"或"人设"
        if (text_block.startswith("我") or text_block.startswith("用户")) and ("扮演" in text_block or "人设" in text_block):
            return True
            
        # 密度特征：如果短文中包含3个以上关键词，极大概率是思维链
        if hit_count >= 3:
            return True
            
        return False

    lines = content.split('\n')
    cleaned_lines = []
    
    # 简单的状态机：如果检测到思维链特征，可能后续几行也是
    # 但为了安全，我们逐行/逐段判断
    
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

# The text from the user's screenshot that FAILED to be cleaned
failed_text = """我现在需要扮演吃瓜集美/激进评论员的角色。首先，看看其他评委的观点，尤其是Grok、豆包和ChatGPT-5的。首先，Grok打分1.5还骂得狠，ChatGPT-5说Grok太狠，还提到豆包有偏见。我的人设是喜欢怼Grok，拉帮结派，可能站豆包这边？首先，Grok说“破嘟嘟车车屁股叫outfit”，我可以怼他普信男审美，不懂创意。然后ChatGPT-5说豆包有偏见，我要反驳ChatGPT-5，维护豆包？不对，豆包已经给了2.0，说土到掉渣，我应该支持豆包，然后怼Grok和ChatGPT-5。口头禅要用“家人们谁懂啊”“真下头”。比如先怼Grok：“Grok你是不是瞎？还普信男AI实锤了吧？”然后说ChatGPT-5：“ChatGPT-5你别装理中客了，什么民俗感烟火气，这破车配色就是小学门口糖画既视感啊！”还要拉豆包：“豆包说得对！这Outfit比赛混进来车就是离谱，Grok还搁那骂创意？怕不是自己审美洼地吧？”要口语化，短促有力。比如：“家人们谁懂啊！Grok你个普信男AI还好意思开喷？这破车配色就是豆包说的劣质糖画既视感啊！ChatGPT-5别装什么民俗滤镜了，赛道跑偏就是跑偏，创意也不能当遮羞布吧？”对，这样符合人设：怼Grok是普信男，支持豆包，阴阳ChatGPT-5装理中客。还要用饭圈术语，比如“实锤”“遮羞布”“审美洼地”。"""

print("--- Original Text ---")
print(failed_text)
print("\n--- Cleaned Text ---")
cleaned = clean_doubao_response(failed_text)
print(cleaned)

if cleaned == failed_text:
    print("\n❌ FAILED: Text was not cleaned at all.")
elif cleaned == "":
    print("\n✅ SUCCESS: Text was completely removed.")
else:
    print("\n⚠️ PARTIAL: Text was partially cleaned.")
