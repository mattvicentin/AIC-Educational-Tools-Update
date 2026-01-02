/**
 * Quiz Tool Handler
 * Manages the quiz panel, generation, and grading flow
 */

(function() {
    'use strict';

    const QUIZ_PANEL_ID = 'quiz-panel';
    const QUIZ_STEPS = {
        CONFIG: 'quiz-step-config',
        QUESTIONS: 'quiz-step-questions',
        RESULTS: 'quiz-step-results'
    };

    let currentQuiz = null;
    let currentAnswers = {};
    let currentQuestionIndex = 0;
    let chatId = null;

    /**
     * Initialize quiz tool
     */
    function initQuizTool() {
        // Get chat ID from URL or data attribute
        const chatMatch = window.location.pathname.match(/\/chat\/(\d+)/);
        chatId = chatMatch ? parseInt(chatMatch[1]) : null;
        
        if (!chatId) {
            const chatContainer = document.querySelector('.chat-container');
            chatId = chatContainer ? parseInt(chatContainer.dataset.chatId) : null;
        }

        if (!chatId) {
            console.warn('Quiz tool: Could not determine chat ID');
            return;
        }

        // Setup event listeners
        setupEventListeners();
        
        // Setup context mode change handler
        const contextModeSelect = document.getElementById('quiz-context-mode');
        if (contextModeSelect) {
            contextModeSelect.addEventListener('change', handleContextModeChange);
        }
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Close button
        const closeBtn = document.getElementById('quiz-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeQuizPanel);
        }

        // Config form submit
        const configForm = document.getElementById('quiz-config-form');
        if (configForm) {
            configForm.addEventListener('submit', handleConfigSubmit);
        }

        // Library add button
        const libraryAddBtn = document.getElementById('quiz-library-add-btn');
        if (libraryAddBtn) {
            libraryAddBtn.addEventListener('click', openLibraryUpload);
        }

        // Library file input
        const libraryFileInput = document.getElementById('quiz-library-file-input');
        if (libraryFileInput) {
            libraryFileInput.addEventListener('change', handleQuizLibraryUpload);
        }

        // Difficulty buttons
        const difficultyButtons = document.querySelectorAll('.quiz-difficulty-btn');
        difficultyButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const difficulty = btn.getAttribute('data-difficulty');
                handleDifficultySelection(difficulty);
            });
        });

        // Question navigation
        const backBtn = document.getElementById('quiz-back-btn');
        const nextBtn = document.getElementById('quiz-next-btn');
        if (backBtn) backBtn.addEventListener('click', goToPreviousQuestion);
        if (nextBtn) nextBtn.addEventListener('click', goToNextQuestion);

        // Results actions
        const retryBtn = document.getElementById('quiz-retry-btn');
        const sendResultsBtn = document.getElementById('quiz-send-results-btn');
        if (retryBtn) retryBtn.addEventListener('click', resetQuiz);
        if (sendResultsBtn) sendResultsBtn.addEventListener('click', sendResultsToChat);

        // Error retry
        const errorRetryBtn = document.getElementById('quiz-error-retry');
        if (errorRetryBtn) {
            errorRetryBtn.addEventListener('click', () => {
                hideError();
                showStep(QUIZ_STEPS.CONFIG);
            });
        }

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !isPanelHidden()) {
                closeQuizPanel();
            }
        });

        // Close on backdrop click
        const backdrop = document.getElementById('quiz-panel-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    closeQuizPanel();
                }
            });
        }
    }

    /**
     * Open quiz panel
     */
    function openQuizPanel() {
        const panel = document.getElementById(QUIZ_PANEL_ID);
        const backdrop = document.getElementById('quiz-panel-backdrop');
        if (!panel) {
            console.error('Quiz panel not found');
            return;
        }

        // Show backdrop first
        if (backdrop) {
            backdrop.classList.remove('hidden');
        }
        
        // Then show panel
        panel.classList.remove('hidden');
        showStep(QUIZ_STEPS.CONFIG);
        resetQuiz();
        
        // Load library documents if needed
        handleContextModeChange();
        
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Close quiz panel
     */
    function closeQuizPanel() {
        const panel = document.getElementById(QUIZ_PANEL_ID);
        const backdrop = document.getElementById('quiz-panel-backdrop');
        
        if (panel) {
            panel.classList.add('hidden');
        }
        
        // Hide backdrop
        if (backdrop) {
            backdrop.classList.add('hidden');
        }
        
        resetQuiz();
    }

    /**
     * Check if panel is hidden
     */
    function isPanelHidden() {
        const panel = document.getElementById(QUIZ_PANEL_ID);
        return !panel || panel.classList.contains('hidden');
    }

    /**
     * Show a specific step
     */
    function showStep(stepId) {
        Object.values(QUIZ_STEPS).forEach(step => {
            const stepEl = document.getElementById(step);
            if (stepEl) {
                stepEl.classList.remove('quiz-step--active');
                stepEl.classList.add('quiz-step--hidden');
            }
        });

        const targetStep = document.getElementById(stepId);
        if (targetStep) {
            targetStep.classList.remove('quiz-step--hidden');
            targetStep.classList.add('quiz-step--active');
        }

        hideLoading();
        hideError();
    }

    /**
     * Handle difficulty selection
     */
    function handleDifficultySelection(difficulty) {
        // Update button active states
        const buttons = document.querySelectorAll('.quiz-difficulty-btn');
        buttons.forEach(btn => {
            if (btn.getAttribute('data-difficulty') === difficulty) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update hidden input
        const hiddenInput = document.getElementById('quiz-difficulty');
        if (hiddenInput) {
            hiddenInput.value = difficulty;
        }
    }

    /**
     * Handle context mode change
     */
    async function handleContextModeChange() {
        const contextMode = document.getElementById('quiz-context-mode')?.value;
        const librarySection = document.getElementById('quiz-library-section');
        
        if (!librarySection) return;

        if (contextMode === 'library' || contextMode === 'both') {
            librarySection.classList.remove('quiz-config-field--hidden');
            await loadLibraryDocuments();
        } else {
            librarySection.classList.add('quiz-config-field--hidden');
        }
    }

    /**
     * Load library documents
     */
    async function loadLibraryDocuments() {
        if (!chatId) return;

        try {
            // Get room ID from chat
            const response = await fetch(`/chat/${chatId}/messages`);
            const data = await response.json();
            
            // Get room ID from chat container
            const chatContainer = document.querySelector('.chat-container');
            const roomId = chatContainer ? parseInt(chatContainer.dataset.roomId) : null;
            
            if (!roomId) {
                showLibraryEmpty();
                return;
            }

            // Fetch documents
            const docsResponse = await fetch(`/api/library/documents?room_id=${roomId}`);
            const docsData = await docsResponse.json();
            
            const documents = docsData.documents || [];
            
            if (documents.length === 0) {
                showLibraryEmpty();
            } else {
                showLibraryList(documents);
            }
        } catch (error) {
            console.error('Failed to load library documents:', error);
            showLibraryEmpty();
        }
    }

    /**
     * Show library empty state
     */
    function showLibraryEmpty() {
        const emptyEl = document.getElementById('quiz-library-empty');
        const listEl = document.getElementById('quiz-library-list');
        
        if (emptyEl) emptyEl.classList.remove('hidden');
        if (listEl) listEl.classList.add('hidden');
    }

    /**
     * Show library document list
     */
    function showLibraryList(documents) {
        const emptyEl = document.getElementById('quiz-library-empty');
        const listEl = document.getElementById('quiz-library-list');
        
        if (emptyEl) emptyEl.classList.add('hidden');
        if (listEl) {
            listEl.classList.remove('hidden');
            listEl.innerHTML = '';
            
            documents.forEach(doc => {
                const item = document.createElement('div');
                item.className = 'quiz-library-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `quiz-doc-${doc.id}`;
                checkbox.value = doc.id;
                checkbox.name = 'library_doc_ids';
                
                const label = document.createElement('label');
                label.className = 'quiz-library-item-label';
                label.htmlFor = `quiz-doc-${doc.id}`;
                label.textContent = doc.name;
                
                const meta = document.createElement('span');
                meta.className = 'quiz-library-item-meta';
                const sizeKB = doc.file_size ? Math.round(doc.file_size / 1024) : 0;
                const uploadedDate = doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '';
                meta.textContent = `${sizeKB} KB • ${uploadedDate}`;
                
                item.appendChild(checkbox);
                item.appendChild(label);
                item.appendChild(meta);
                listEl.appendChild(item);
            });
        }
    }

    /**
     * Open library upload - triggers the file input
     */
    function openLibraryUpload() {
        const fileInput = document.getElementById('quiz-library-file-input');
        if (fileInput) {
            fileInput.click();
        }
    }

    /**
     * Handle file upload for quiz panel
     */
    async function handleQuizLibraryUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!chatId) {
            showError('Chat ID not available. Please refresh the page.');
            event.target.value = '';
            return;
        }

        // Get room ID
        const chatContainer = document.querySelector('.chat-container');
        const roomId = chatContainer ? parseInt(chatContainer.dataset.roomId) : null;
        
        if (!roomId) {
            showError('Room ID not available. Please refresh the page.');
            event.target.value = '';
            return;
        }

        const statusDiv = document.getElementById('quiz-library-upload-status');
        const emptyEl = document.getElementById('quiz-library-empty');
        const listEl = document.getElementById('quiz-library-list');
        
        // Show upload status
        if (statusDiv) {
            statusDiv.classList.remove('hidden');
            statusDiv.textContent = 'Uploading...';
            statusDiv.className = 'quiz-library-upload-status';
        }

        // VALIDATION: Check file size against available storage (same as library tool)
        const STORAGE_LIMIT_BYTES = 10 * 1024 * 1024; // 10 MB
        const fileSizeBytes = file.size;
        const fileSizeMB = (fileSizeBytes / (1024 * 1024)).toFixed(2);
        
        try {
            // Get current storage usage
            const statsResponse = await fetch(`/api/library/storage/stats?room_id=${roomId}`);
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                const currentUsageBytes = stats.used_bytes;
                const availableBytes = STORAGE_LIMIT_BYTES - currentUsageBytes;
                const availableMB = (availableBytes / (1024 * 1024)).toFixed(2);
                
                // Check if file would exceed storage limit
                if (fileSizeBytes > availableBytes) {
                    if (statusDiv) {
                        statusDiv.textContent = `❌ File size (${fileSizeMB} MB) exceeds available storage (${availableMB} MB)`;
                        statusDiv.className = 'quiz-library-upload-status quiz-library-upload-status--error';
                    }
                    event.target.value = '';
                    setTimeout(() => {
                        if (statusDiv) statusDiv.classList.add('hidden');
                    }, 5000);
                    return;
                }
            }
        } catch (error) {
            console.error('Error checking storage:', error);
            // Continue with upload if we can't check storage (graceful degradation)
        }

        const formData = new FormData();
        formData.append('file', file);
        
        try {
            if (statusDiv) {
                statusDiv.textContent = 'Processing...';
            }

            const response = await fetch(`/api/library/upload?room_id=${roomId}`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Upload failed');
            }
            
            const result = await response.json();
            
            // Show success
            if (statusDiv) {
                statusDiv.textContent = '✓ Upload successful!';
                statusDiv.className = 'quiz-library-upload-status quiz-library-upload-status--success';
            }
            
            // Clear file input
            event.target.value = '';
            
            // Refresh library documents list
            await loadLibraryDocuments();
            
            // Hide status after a moment
            setTimeout(() => {
                if (statusDiv) statusDiv.classList.add('hidden');
            }, 2000);
            
        } catch (error) {
            console.error('Upload error:', error);
            if (statusDiv) {
                statusDiv.textContent = `❌ ${error.message || 'Upload failed'}`;
                statusDiv.className = 'quiz-library-upload-status quiz-library-upload-status--error';
            }
            event.target.value = '';
            
            // Hide error after 5 seconds
            setTimeout(() => {
                if (statusDiv) statusDiv.classList.add('hidden');
            }, 5000);
        }
    }

    /**
     * Handle config form submit
     */
    async function handleConfigSubmit(e) {
        e.preventDefault();
        
        if (!chatId) {
            showError('Chat ID not found');
            return;
        }

        const formData = new FormData(e.target);
        const questionCount = parseInt(formData.get('question_count'));
        const contextMode = formData.get('context_mode');
        const difficulty = formData.get('difficulty') || 'average';
        const instructions = formData.get('instructions') || '';
        
        // Get selected library documents
        const libraryDocIds = [];
        if (contextMode === 'library' || contextMode === 'both') {
            const checkboxes = document.querySelectorAll('#quiz-library-list input[type="checkbox"]:checked');
            checkboxes.forEach(cb => libraryDocIds.push(parseInt(cb.value)));
            
            if (contextMode === 'library' && libraryDocIds.length === 0) {
                showError('Please select at least one library document');
                return;
            }
        }

        // Show loading
        showLoading('Generating questions...');

        try {
            const response = await fetch('/api/quiz/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    chat_id: chatId,
                    question_count: questionCount,
                    context_mode: contextMode,
                    difficulty: difficulty,
                    library_doc_ids: libraryDocIds,
                    instructions: instructions
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate quiz');
            }

            if (!data.success) {
                throw new Error(data.error || 'Quiz generation failed');
            }

            // Store quiz and show questions
            currentQuiz = data.quiz;
            currentAnswers = {};
            currentQuestionIndex = 0;
            
            showStep(QUIZ_STEPS.QUESTIONS);
            renderQuestions();
            
        } catch (error) {
            console.error('Quiz generation error:', error);
            showError(error.message || 'Failed to generate quiz. Please try again.');
        }
    }

    /**
     * Render questions
     */
    function renderQuestions() {
        if (!currentQuiz || !currentQuiz.questions) return;

        const container = document.getElementById('quiz-questions-container');
        if (!container) return;

        container.innerHTML = '';
        
        currentQuiz.questions.forEach((question, index) => {
            const questionEl = document.createElement('div');
            questionEl.className = 'quiz-question';
            questionEl.id = `quiz-question-${index}`;
            questionEl.style.display = index === currentQuestionIndex ? 'block' : 'none';
            
            const questionText = document.createElement('div');
            questionText.className = 'quiz-question-text';
            questionText.textContent = `${index + 1}. ${question.text}`;
            
            const choicesContainer = document.createElement('div');
            choicesContainer.className = 'quiz-choices';
            
            question.choices.forEach((choice, choiceIndex) => {
                const choiceBtn = document.createElement('button');
                choiceBtn.type = 'button';
                choiceBtn.className = 'quiz-choice';
                choiceBtn.textContent = choice;
                
                if (currentAnswers[question.id] === choiceIndex) {
                    choiceBtn.classList.add('selected');
                }
                
                choiceBtn.addEventListener('click', () => {
                    selectAnswer(question.id, choiceIndex, index);
                });
                
                choicesContainer.appendChild(choiceBtn);
            });
            
            questionEl.appendChild(questionText);
            questionEl.appendChild(choicesContainer);
            container.appendChild(questionEl);
        });

        updateQuestionCounter();
        updateNavigationButtons();
    }

    /**
     * Select an answer
     */
    function selectAnswer(questionId, choiceIndex, questionIndex) {
        currentAnswers[questionId] = choiceIndex;
        
        // Update UI
        const questionEl = document.getElementById(`quiz-question-${questionIndex}`);
        if (questionEl) {
            const choices = questionEl.querySelectorAll('.quiz-choice');
            choices.forEach((choice, idx) => {
                choice.classList.remove('selected');
                if (idx === choiceIndex) {
                    choice.classList.add('selected');
                }
            });
        }
        
        updateNavigationButtons();
        
        // Auto-advance if not last question
        if (currentQuestionIndex < currentQuiz.questions.length - 1) {
            setTimeout(() => {
                goToNextQuestion();
            }, 300);
        }
    }

    /**
     * Update question counter
     */
    function updateQuestionCounter() {
        const counter = document.getElementById('quiz-question-counter');
        if (counter && currentQuiz) {
            counter.textContent = `Question ${currentQuestionIndex + 1} of ${currentQuiz.questions.length}`;
        }
    }

    /**
     * Update navigation buttons
     */
    function updateNavigationButtons() {
        const backBtn = document.getElementById('quiz-back-btn');
        const nextBtn = document.getElementById('quiz-next-btn');
        
        if (backBtn) {
            backBtn.disabled = currentQuestionIndex === 0;
        }
        
        if (nextBtn) {
            const currentQuestion = currentQuiz.questions[currentQuestionIndex];
            const hasAnswer = currentAnswers[currentQuestion.id] !== undefined;
            nextBtn.disabled = !hasAnswer;
            
            if (currentQuestionIndex === currentQuiz.questions.length - 1) {
                nextBtn.textContent = 'Submit';
            } else {
                nextBtn.textContent = 'Next';
            }
        }
    }

    /**
     * Go to previous question
     */
    function goToPreviousQuestion() {
        if (currentQuestionIndex > 0) {
            const prevQuestion = document.getElementById(`quiz-question-${currentQuestionIndex}`);
            if (prevQuestion) prevQuestion.style.display = 'none';
            
            currentQuestionIndex--;
            
            const currentQuestion = document.getElementById(`quiz-question-${currentQuestionIndex}`);
            if (currentQuestion) currentQuestion.style.display = 'block';
            
            updateQuestionCounter();
            updateNavigationButtons();
        }
    }

    /**
     * Go to next question or submit
     */
    async function goToNextQuestion() {
        const currentQuestion = currentQuiz.questions[currentQuestionIndex];
        const hasAnswer = currentAnswers[currentQuestion.id] !== undefined;
        
        if (!hasAnswer) return;
        
        if (currentQuestionIndex < currentQuiz.questions.length - 1) {
            const currentQuestionEl = document.getElementById(`quiz-question-${currentQuestionIndex}`);
            if (currentQuestionEl) currentQuestionEl.style.display = 'none';
            
            currentQuestionIndex++;
            
            const nextQuestionEl = document.getElementById(`quiz-question-${currentQuestionIndex}`);
            if (nextQuestionEl) nextQuestionEl.style.display = 'block';
            
            updateQuestionCounter();
            updateNavigationButtons();
        } else {
            // Submit quiz
            await submitQuiz();
        }
    }

    /**
     * Submit quiz for grading
     */
    async function submitQuiz() {
        if (!currentQuiz) return;

        showLoading('Submitting answers...');

        try {
            const response = await fetch(`/api/quiz/${currentQuiz.id}/grade`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    answers: currentAnswers
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to grade quiz');
            }

            if (!data.success) {
                throw new Error(data.error || 'Grading failed');
            }

            // Show results
            showResults(data);
            
        } catch (error) {
            console.error('Quiz submission error:', error);
            showError(error.message || 'Failed to submit quiz. Please try again.');
        }
    }

    /**
     * Show results
     */
    function showResults(data) {
        const resultsContainer = document.getElementById('quiz-results-container');
        const scoreDisplay = document.getElementById('quiz-score-display');
        
        if (!resultsContainer || !scoreDisplay) return;

        // Update score display
        scoreDisplay.textContent = `${data.score} / ${data.total}`;

        // Render results
        resultsContainer.innerHTML = '';
        
        data.results.forEach((result, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = `quiz-result-item ${result.is_correct ? 'correct' : 'incorrect'}`;
            
            const questionText = document.createElement('div');
            questionText.className = 'quiz-result-question';
            questionText.textContent = `${index + 1}. ${result.question_text}`;
            
            const answerText = document.createElement('div');
            answerText.className = 'quiz-result-answer';
            const userChoice = currentQuiz.questions[index].choices[result.user_answer];
            const correctChoice = currentQuiz.questions[index].choices[result.correct_answer];
            answerText.textContent = `Your answer: ${userChoice} ${result.is_correct ? '✓' : '✗'} | Correct: ${correctChoice}`;
            
            const explanation = document.createElement('div');
            explanation.className = 'quiz-result-explanation';
            explanation.textContent = result.explanation || 'No explanation provided.';
            
            resultItem.appendChild(questionText);
            resultItem.appendChild(answerText);
            resultItem.appendChild(explanation);
            resultsContainer.appendChild(resultItem);
        });

        showStep(QUIZ_STEPS.RESULTS);
    }

    /**
     * Send results to chat
     */
    async function sendResultsToChat() {
        if (!currentQuiz || !chatId) {
            console.error('Cannot send results: missing quiz or chatId');
            alert('Error: Quiz data not available. Please try again.');
            return;
        }

        const scoreDisplay = document.getElementById('quiz-score-display');
        const score = scoreDisplay ? scoreDisplay.textContent : 'N/A';

        // Build detailed results text
        let resultsText = `**Quiz Results: ${score}**\n\n`;
        resultsText += `Quiz generated from ${currentQuiz.context_mode} context with ${currentQuiz.question_count} questions.\n\n`;
        
        // Add per-question results if available
        const resultsContainer = document.getElementById('quiz-results-container');
        if (resultsContainer) {
            const resultItems = resultsContainer.querySelectorAll('.quiz-result-item');
            resultItems.forEach((item, index) => {
                const questionText = item.querySelector('.quiz-result-question')?.textContent || '';
                const answerText = item.querySelector('.quiz-result-answer')?.textContent || '';
                const explanation = item.querySelector('.quiz-result-explanation')?.textContent || '';
                
                resultsText += `**Question ${index + 1}:** ${questionText}\n`;
                resultsText += `${answerText}\n`;
                if (explanation) {
                    resultsText += `*Explanation:* ${explanation}\n`;
                }
                resultsText += '\n';
            });
        }

        try {
            // Get CSRF token
            const csrfToken = getCsrfToken();
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }

            // Post message to chat using fetch (better error handling)
            const response = await fetch(`/chat/${chatId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'content': resultsText,
                    'ai_response': '0',
                    'csrf_token': csrfToken
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to send message to chat');
            }

            // Success - close panel and refresh messages
            alert('Quiz results sent to chat successfully!');
            closeQuizPanel();
            
            // Refresh chat messages if function exists
            if (typeof pollNewMessages === 'function') {
                pollNewMessages();
            } else if (typeof window.chatView && typeof window.chatView.loadMessages === 'function') {
                window.chatView.loadMessages();
            }
            
        } catch (error) {
            console.error('Failed to send results to chat:', error);
            alert(`Failed to send results to chat: ${error.message}\n\nYou can copy the results manually from the quiz panel.`);
        }
    }

    /**
     * Get CSRF token from meta tag or form
     */
    function getCsrfToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        // Try form input
        const form = document.querySelector('form[method="POST"]');
        if (form) {
            const csrfInput = form.querySelector('input[name="csrf_token"]');
            if (csrfInput) {
                return csrfInput.value;
            }
        }
        
        return null;
    }

    /**
     * Reset quiz
     */
    function resetQuiz() {
        currentQuiz = null;
        currentAnswers = {};
        currentQuestionIndex = 0;
        
        const configForm = document.getElementById('quiz-config-form');
        if (configForm) {
            configForm.reset();
            const questionCountInput = document.getElementById('quiz-question-count');
            if (questionCountInput) questionCountInput.value = 5;
        }
        
        // Reset library section
        const librarySection = document.getElementById('quiz-library-section');
        if (librarySection) {
            librarySection.classList.add('quiz-config-field--hidden');
        }
        
        // Reset context mode
        const contextModeSelect = document.getElementById('quiz-context-mode');
        if (contextModeSelect) {
            contextModeSelect.value = 'chat';
        }

        // Reset difficulty to default
        handleDifficultySelection('average');
        
        // Clear library list
        const libraryList = document.getElementById('quiz-library-list');
        if (libraryList) {
            libraryList.innerHTML = '';
            libraryList.classList.add('hidden');
        }
        const libraryEmpty = document.getElementById('quiz-library-empty');
        if (libraryEmpty) {
            libraryEmpty.classList.remove('hidden');
        }
        
        // Switch back to config step
        showStep(QUIZ_STEPS.CONFIG);
        hideError();
        hideLoading();
    }

    /**
     * Show loading state
     */
    function showLoading(text = 'Loading...') {
        const loadingEl = document.getElementById('quiz-loading');
        const loadingText = document.getElementById('quiz-loading-text');
        
        if (loadingEl) loadingEl.classList.remove('hidden');
        if (loadingText) loadingText.textContent = text;
    }

    /**
     * Hide loading state
     */
    function hideLoading() {
        const loadingEl = document.getElementById('quiz-loading');
        if (loadingEl) loadingEl.classList.add('hidden');
    }

    /**
     * Show error
     */
    function showError(message) {
        const errorEl = document.getElementById('quiz-error');
        const errorText = document.getElementById('quiz-error-text');
        
        if (errorEl) errorEl.classList.remove('hidden');
        if (errorText) errorText.textContent = message;
        
        hideLoading();
    }

    /**
     * Hide error
     */
    function hideError() {
        const errorEl = document.getElementById('quiz-error');
        if (errorEl) errorEl.classList.add('hidden');
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initQuizTool);
    } else {
        initQuizTool();
    }

    // Export for external use
    window.quizTool = {
        open: openQuizPanel,
        close: closeQuizPanel
    };

})();

