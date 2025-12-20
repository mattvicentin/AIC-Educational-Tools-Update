# Step 1: Consolidate Tools - Implementation Guide

## What We're Doing
Move Learning Progress into Tools accordion
Add tool-stack wrapper with 3 mount points
Remove Learning Progress from header

---

## PART A: Update Tools Section (Add Content)

**FIND** (around line 143):
```html
            <div class="sidebar-panel space-y-4">
                <!-- Document generation dropdown is injected here via restore-document-generation.js -->
                <div id="tone-critique-mount"></div>
            </div>
        </details>
```

**REPLACE WITH:**
```html
            <div class="sidebar-panel">
                <div class="tool-stack space-y-4">
                    <!-- 1. Learning Progress Card -->
                    <section id="learning-progress-card" class="space-y-2">
                        <div class="flex items-center justify-between mb-2">
                            <h4 class="text-sm font-medium text-foreground">Learning Progress</h4>
                            <button id="assess-progress-btn" 
                                    class="text-xs px-2 py-1 bg-primary/10 text-primary rounded hover:bg-primary/20 transition-colors"
                                    onclick="assessLearningProgress()">
                                🔍 Assess Progress
                            </button>
                        </div>
                        
                        <!-- Progress Status Display -->
                        <div id="progress-status" class="hidden">
                            <div id="progress-content" class="p-3 rounded-md text-xs">
                                <!-- Progress content will be populated by JavaScript -->
                            </div>
                        </div>
                        
                        <!-- Loading State -->
                        <div id="progress-loading" class="hidden">
                            <div class="p-3 rounded-md text-xs text-muted-foreground">
                                <div class="flex items-center gap-2">
                                    <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-primary"></div>
                                    Analyzing your progress...
                                </div>
                            </div>
                        </div>
                    </section>
                    
                    <!-- 2. Tone & Critique Card (injected via base.html) -->
                    <div id="tone-critique-mount"></div>
                    
                    <!-- 3. Document Generation Card (injected via restore-document-generation.js) -->
                    <div id="doc-gen-mount"></div>
                </div>
            </div>
        </details>
```

---

## PART B: Remove Learning Progress from Header

**FIND** (around line 104):
```html
                <!-- Learning Progress Assessment -->
                <div class="learning-progress-section">
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="text-sm font-medium text-foreground">Learning Progress</h4>
                        <button id="assess-progress-btn" 
                                class="text-xs px-2 py-1 bg-primary/10 text-primary rounded hover:bg-primary/20 transition-colors"
                                onclick="assessLearningProgress()">
                            🔍 Assess Progress
                        </button>
                    </div>
                    
                    <!-- Progress Status Display -->
                    <div id="progress-status" class="hidden">
                        <div id="progress-content" class="p-3 rounded-md text-xs">
                            <!-- Progress content will be populated by JavaScript -->
                        </div>
                    </div>
                    
                    <!-- Loading State -->
                    <div id="progress-loading" class="hidden">
                        <div class="p-3 rounded-md text-xs text-muted-foreground">
                            <div class="flex items-center gap-2">
                                <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-primary"></div>
                                Analyzing your progress...
                            </div>
                        </div>
                    </div>
                </div>
```

**DELETE IT** (remove entire block)

---

## PART C: Update restore-document-generation.js

**FIND** (line 82):
```javascript
const toolsPanel = document.querySelector('.sidebar-section[data-section="tools"] .sidebar-panel');
if (toolsPanel) {
    // Insert at top of Tools panel
    toolsPanel.insertBefore(docDiv, toolsPanel.firstChild);
```

**REPLACE WITH:**
```javascript
// Try new doc-gen-mount first
const docMount = document.getElementById('doc-gen-mount');
if (docMount) {
    docMount.appendChild(docDiv);
    console.log('📦 Document dropdown injected into doc-gen-mount (tool-stack)');
} else {
    // Fallback: insert at top of Tools panel
    const toolsPanel = document.querySelector('.sidebar-section[data-section="tools"] .sidebar-panel');
    if (toolsPanel) {
        toolsPanel.insertBefore(docDiv, toolsPanel.firstChild);
```

---

## VERIFICATION

After changes:

```bash
# Check structure
grep -c "learning-progress-section" templates/chat/view.html
# Should be: 0 (removed from header)

grep -c "learning-progress-card" templates/chat/view.html  
# Should be: 1 (in Tools section)

grep -c "doc-gen-mount" templates/chat/view.html
# Should be: 1 (new mount point)

# Verify IDs preserved
grep "assess-progress-btn\|progress-status\|progress-loading" templates/chat/view.html
# All should still exist (just moved)
```

---

## TESTING AFTER IMPLEMENTATION

1. Desktop:
   - Tools section should be expanded
   - Should see: Learning Progress, Tone mount, Doc gen mount
   - Click "Assess Progress" → Should work
   - Document dropdown should appear in doc-gen-mount

2. Console:
   - Should see: "Document dropdown injected into doc-gen-mount"
   
3. Verify IDs:
   ```javascript
   console.log('Progress button:', !!document.getElementById('assess-progress-btn'));
   console.log('Progress status:', !!document.getElementById('progress-status'));
   // Both should be true
   ```

---

## COMMIT

```bash
git add templates/chat/view.html src/app/static/js/restore-document-generation.js
git commit -m "refactor: Consolidate tools into accordion with tool-stack

STEP 1: Tools Consolidation

MOVED:
- Learning Progress from header → Tools panel
- Kept all IDs unchanged (#assess-progress-btn, etc.)

ADDED:
- tool-stack wrapper (space-y-4)
- #doc-gen-mount for document dropdown
- Organized order: Progress, Tone, Documents

UPDATED:
- restore-document-generation.js targets doc-gen-mount
- Fallback to old logic if mount not found

RESULT:
All tools consolidated in one collapsible section
Clean separation: Always-visible header vs Tools utilities"
```

---

**Use this guide to make the changes!**
Then I'll review and help with any issues.
