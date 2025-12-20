# Adaptive Archetype Prompts - Implementation Guide

**Date**: October 6, 2025  
**Status**: ✅ Implemented & Deployed  
**Commit**: `a9f38a8`  
**Feature Flag**: `ENABLE_ARCHETYPE_PROMPTS=true` (ON by default)

---

## 🎯 **What Was Implemented**

**System**: Cognitive archetype inference that adapts AI expression style to the learning step's cognitive demands.

**Problem Solved**: AI responses were too list-heavy and generic across all learning contexts.

**Solution**: Infer cognitive archetype from step characteristics, apply appropriate guardrails and expression styles.

---

## 🧠 **The 8 Cognitive Archetypes**

| Archetype | When Detected | Expression Style | Example Keywords |
|-----------|---------------|------------------|------------------|
| **Divergent** | Exploring, brainstorming | Conversational questions, examples | explore, imagine, brainstorm |
| **Convergent** | Focusing, narrowing | Concise prose, clarifying questions | narrow, focus, refine, specify |
| **Analytical** | Investigating, examining | Flowing prose, cause-effect | analyze, why, cause, trace |
| **Comparative** | Contrasting, evaluating | Narrative comparisons | compare, contrast, versus |
| **Generative** | Creating, composing | Mixed guidance + structure | draft, write, create, compose |
| **Technical** | Procedures, formatting | Numbered steps appropriate | procedure, citation, algorithm |
| **Predictive** | Forecasting, modeling | Analytical narrative | forecast, predict, scenario |
| **Metacognitive** | Reflecting, assessing | Coaching voice, questions | reflect, revise, evaluate own |

---

## 🔄 **How It Works**

### **Step 1: Get Base Prompt**
```python
# From CustomPrompt (database) or BASE_MODES
base_prompt = "You are an expert instructor in..."
step_title = "1. Explore market opportunities"
```

### **Step 2: Infer Archetype**
```python
text = "1. Explore market opportunities You are an expert..."
# Keywords: "explore" → matches "divergent"
archetype = "divergent"
```

### **Step 3: Apply Enhancements**
```python
base_prompt += """
CONSTRAINT: Ask 2-3 open-ended questions. Do not present conclusions.
STYLE: Use conversational dialogue with examples. Avoid numbered lists.
STYLE+: Favor cohesive paragraphs or short examples.
LENGTH: Target 150-200 words unless the question requires depth.
"""
```

### **Step 4: Add Learning Context**
```python
# Existing system continues
base_prompt += "\n\nLEARNING CONTEXT FROM PREVIOUS DISCUSSIONS:\n..."
```

---

## 📊 **Coverage & Impact**

### **Rooms Affected**:
- ✅ **Custom/bespoke rooms**: 100% covered
- ✅ **Template rooms** (study-group, business-hub, etc.): 100% covered
- ⚪ **Legacy academic-essay**: Skipped (preserves existing behavior)
- **Total coverage**: ~95% of all rooms

### **Immediate Impact**:
- Every AI response in covered rooms gets archetype enhancement
- No database migration needed
- No UI changes needed
- Works with existing CustomPrompt system

---

## 🧪 **How to Test**

### **Test 1: Divergent (Explore Step)**

**Create/open a chat** in explore/brainstorm mode

**Send**: "I'm interested in renewable energy"

**Expected AI Response**:
```
✅ GOOD (Divergent style):
"What specifically draws you to renewable energy? Is it the 
environmental impact, the technological innovation, or perhaps 
the economic opportunities? Let me share an example..."

❌ OLD (List-heavy):
"Here are three aspects to consider:
1. Environmental benefits
2. Technological challenges
3. Economic factors"
```

---

### **Test 2: Analytical (Analysis Step)**

**In an analysis/investigate mode**

**Send**: "How does social media affect democracy?"

**Expected AI Response**:
```
✅ GOOD (Analytical style):
"The relationship between social media and democracy involves 
several interconnected mechanisms. When information spreads 
rapidly without verification, it creates echo chambers that 
reinforce existing beliefs rather than encouraging critical 
examination..."

❌ OLD (List-heavy):
"Social media affects democracy through:
1. Echo chambers
2. Misinformation spread
3. Polarization
4. Reduced civil discourse"
```

---

### **Test 3: Technical (Citation/Procedure Step)**

**In citation or procedure mode**

**Send**: "How do I cite a journal article?"

**Expected AI Response**:
```
✅ GOOD (Technical style - lists ARE appropriate):
"For a journal article in APA format, you need:
1. Author last name, initials
2. Publication year in parentheses
3. Article title
4. Journal name in italics
5. Volume number..."

✅ OLD: Would also use lists (no change needed here)
```

---

### **Test 4: Metacognitive (Reflection Step)**

**In reflect/review mode**

**Send**: "What did I learn?"

**Expected AI Response**:
```
✅ GOOD (Metacognitive style):
"Looking back at your exploration, you've developed a more 
nuanced understanding of how environmental and economic factors 
intersect. What surprised you most about this process? How might 
this change your approach to future research?"

❌ OLD (List-heavy):
"You learned:
1. How to narrow research questions
2. Source evaluation techniques
3. Argument development"
```

---

## 🔍 **Debugging & Verification**

### **Check if Archetype is Applied**

**Railway logs** should show:
```
🎭 Archetype: divergent for mode=step_1, step=1. Explore market opportunities
```

### **Check in Browser Console**

The AI response should:
- Be more conversational in explore/analytical modes
- Have fewer numbered lists
- Use more examples and narratives
- Keep technical/procedural modes structured

### **Manual Verification**

Compare responses in:
- **Same room, different steps** - Should vary in style
- **Different archetypes** - Divergent vs Technical should be very different
- **Legacy essay rooms** - Should be unchanged

---

## 🚨 **If Issues Arise**

### **Problem: Responses Too Long**

**Symptom**: AI responses exceeding 300+ words

**Fix**: Adjust length guidance
```python
base_prompt += "\n\nLENGTH: Keep under 180 words. Be concise."
```

### **Problem: Wrong Archetype Detected**

**Symptom**: "Compare theories" detected as "divergent" instead of "comparative"

**Fix**: Adjust keyword priority in ARCHETYPE_KEYWORDS
```python
# Move "compare" higher in the list
("comparative", ["compare", "contrast", ...]),  # Check first
```

### **Problem: Still Too Many Lists**

**Symptom**: Responses still list-heavy despite archetype

**Fix**: Strengthen style guidance
```python
"style": "STYLE: Write in flowing paragraphs. Do NOT use numbered lists or bullet points."
```

### **Problem: Breaks Something**

**Immediate rollback**:
```bash
# Option A: Disable feature flag (30 seconds)
railway variables set ENABLE_ARCHETYPE_PROMPTS=false

# Option B: Revert to stable tag (2 minutes)
git reset --hard stable-before-archetypes
git push origin feature/railway-deployment --force
```

---

## 📋 **Rollback Procedures**

### **Quick Disable** (Keep code, disable feature)
```bash
railway variables set ENABLE_ARCHETYPE_PROMPTS=false
# Or set to "false" in Railway dashboard
```

### **Full Rollback** (Remove code)
```bash
git reset --hard stable-before-archetypes
git push origin feature/railway-deployment --force
```

### **Selective Rollback** (Revert just this commit)
```bash
git revert a9f38a8
git push origin feature/railway-deployment
```

---

## 🎓 **Understanding Archetype Inference**

### **Example 1: Business Room**

**Step**: "2. Market Analysis and Competitive Research"  
**AI Instruction**: "Help students analyze market trends..."

**Inference**:
```
text = "market analysis analyze market trends"
Keywords match: "analyze" → analytical
Archetype: analytical
```

**Result**: Flowing analytical prose, not lists

---

### **Example 2: Creative Studio**

**Step**: "1. Explore Creative Concepts"  
**AI Instruction**: "Help students explore artistic ideas..."

**Inference**:
```
text = "explore creative concepts explore artistic ideas"
Keywords match: "explore" → divergent
Archetype: divergent
```

**Result**: Conversational dialogue with examples

---

### **Example 3: Study Group**

**Step**: "3. Review and Practice"  
**AI Instruction**: "Guide through review techniques..."

**Inference**:
```
text = "review practice guide through review"
Keywords match: "review" → metacognitive
Archetype: metacognitive
```

**Result**: Coaching voice with reflective question

---

## ✅ **Success Metrics**

### **Quantitative** (Can measure with telemetry)
- [ ] Bullet density decreases in divergent/analytical modes
- [ ] Response length stays 150-250 words
- [ ] No errors or failures

### **Qualitative** (User feedback)
- [ ] Responses feel more conversational in explore steps
- [ ] Technical steps still provide clear procedures
- [ ] Students report better engagement
- [ ] AI "sounds like a teacher" appropriate to the step

---

## 📞 **Testing Checklist**

- [ ] Test divergent mode (explore step) - conversational?
- [ ] Test analytical mode (analyze step) - flowing prose?
- [ ] Test technical mode (citation step) - still structured?
- [ ] Test comparative mode (compare step) - narrative contrast?
- [ ] Test metacognitive mode (reflect step) - coaching voice?
- [ ] Test legacy essay room - unchanged behavior?
- [ ] Check Railway logs for archetype detection
- [ ] Monitor for increased verbosity
- [ ] Check response times (should be same)

---

## 🔧 **Configuration**

### **Enable/Disable**

**Railway Dashboard** → Variables:
```
ENABLE_ARCHETYPE_PROMPTS = true   # Feature ON (default)
ENABLE_ARCHETYPE_PROMPTS = false  # Feature OFF (rollback)
```

### **Future Tuning** (If needed)

**Add keywords** for better detection:
```python
("divergent", ["explore", "brainstorm", "ideate", ...]),  # Add more
```

**Adjust length targets**:
```python
base_prompt += "\n\nLENGTH: Target 120-150 words."  # Shorter
```

**Add new archetype** (if pattern emerges):
```python
"synthetic": {
    "guard": "CONSTRAINT: Integrate multiple perspectives...",
    "style": "STYLE: Weave together ideas..."
}
```

---

## 📊 **Current Status**

**Deployed**: ✅ Commit `a9f38a8`  
**Flag**: ON by default  
**Coverage**: ~95% of rooms  
**Risk**: Low (feature-flagged, reversible)  
**Rollback**: Tag `stable-before-archetypes` available  

---

**Next**: Test on various room types and monitor AI response quality! 🎯
