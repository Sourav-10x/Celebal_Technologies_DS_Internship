/* ==========================================================================
   ALEXA - AI-POWERED STUDY ASSISTANT JAVASCRIPT ENGINE
   Canvas Particles, RAG Engine Integration, Voice STT/TTS, 3D Flashcards & Quizzes
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

  // App State
  const state = {
    documents: [],
    flashcards: [],
    currentCardIndex: 0,
    quizQuestions: [],
    currentQuizIndex: 0,
    quizScore: 0,
    selectedDocFilter: '',
    isListening: false,
    recognition: null,
    synth: window.speechSynthesis
  };

  // =========================================================================
  // 1. PARTICLE CANVAS ANIMATION ENGINE
  // =========================================================================
  const initCanvas = () => {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    const particles = [];
    const particleCount = 45;

    const symbols = [
      '∑', 'λ', 'Ω', 'π', 'f(x)',
      '∇', 'θ', 'RAG', 'AI', '∫'
    ];

    class Particle {
      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * 0.6;
        this.vy = (Math.random() - 0.5) * 0.6;
        this.radius = Math.random() * 2 + 1;
        this.alpha = Math.random() * 0.5 + 0.2;

        this.symbol =
          Math.random() > 0.6
            ? symbols[Math.floor(Math.random() * symbols.length)]
            : null;
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;

        if (this.x < 0 || this.x > width) {
          this.vx *= -1;
        }

        if (this.y < 0 || this.y > height) {
          this.vy *= -1;
        }
      }

      draw() {
        ctx.save();
        ctx.globalAlpha = this.alpha;

        if (this.symbol) {
          ctx.font = '12px "Fira Code", monospace';
          ctx.fillStyle = '#06b6d4';
          ctx.fillText(this.symbol, this.x, this.y);
        } else {
          ctx.beginPath();
          ctx.arc(
            this.x,
            this.y,
            this.radius,
            0,
            Math.PI * 2
          );
          ctx.fillStyle = '#6366f1';
          ctx.fill();
        }

        ctx.restore();
      }
    }

    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }

    const animate = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw connection lines
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;

          const dist = Math.sqrt(
            dx * dx + dy * dy
          );

          if (dist < 110) {
            ctx.save();

            ctx.globalAlpha =
              (1 - dist / 110) * 0.15;

            ctx.strokeStyle = '#6366f1';
            ctx.lineWidth = 1;

            ctx.beginPath();

            ctx.moveTo(
              particles[i].x,
              particles[i].y
            );

            ctx.lineTo(
              particles[j].x,
              particles[j].y
            );

            ctx.stroke();

            ctx.restore();
          }
        }
      }

      particles.forEach(p => {
        p.update();
        p.draw();
      });

      requestAnimationFrame(animate);
    };

    animate();

    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });
  };

  initCanvas();

  // =========================================================================
  // 2. WALLPAPER THEME SWITCHER
  // =========================================================================
  const setupWallpapers = () => {
    const dots = document.querySelectorAll('.wp-dot');

    const savedTheme =
      localStorage.getItem('alexa_theme') ||
      'wallpaper-cosmos';

    document.body.className = savedTheme;

    dots.forEach(dot => {

      if (dot.dataset.theme === savedTheme) {
        dot.classList.add('active');
      } else {
        dot.classList.remove('active');
      }

      dot.addEventListener('click', () => {

        dots.forEach(d =>
          d.classList.remove('active')
        );

        dot.classList.add('active');

        const theme = dot.dataset.theme;

        document.body.className = theme;

        localStorage.setItem(
          'alexa_theme',
          theme
        );
      });
    });
  };

  setupWallpapers();

  // =========================================================================
  // 3. NAVIGATION VIEW SWITCHER
  // =========================================================================
  const navItems =
    document.querySelectorAll('.nav-item');

  const viewSections =
    document.querySelectorAll('.view-section');

  const pageHeading =
    document.getElementById('page-heading');

  const pageSubheading =
    document.getElementById('page-subheading');

  const headersMap = {
    dashboard: {
      title: 'Study Workspace',
      sub: 'Upload documents, ingest vector notes, and manage knowledge base.'
    },

    chat: {
      title: 'RAG Context Chat',
      sub: 'Ask questions in natural language and get cited, context-based answers.'
    },

    flashcards: {
      title: 'Flashcards Arena',
      sub: 'Active recall study deck generated automatically from your notes.'
    },

    quiz: {
      title: 'AI Quiz Studio',
      sub: 'Test your understanding with automated context-based multiple choice quizzes.'
    },

    voice: {
      title: 'Alexa Voice Hub',
      sub: 'Full voice interaction for hands-free audio studying.'
    },

    summary: {
      title: 'Analytics & Summary',
      sub: 'Executive summaries, key takeaways, and concept breakdown.'
    },

    settings: {
      title: 'Configuration',
      sub: 'API Keys and assistant preferences.'
    }
  };

  const switchView = (viewName) => {

    navItems.forEach(item => {

      if (item.dataset.view === viewName) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }

    });

    viewSections.forEach(sec => {

      if (sec.id === `view-${viewName}`) {
        sec.classList.add('active');
      } else {
        sec.classList.remove('active');
      }

    });

    if (headersMap[viewName]) {

      pageHeading.textContent =
        headersMap[viewName].title;

      pageSubheading.textContent =
        headersMap[viewName].sub;
    }

    if (
      viewName === 'flashcards' &&
      state.flashcards.length === 0
    ) {
      loadFlashcards();
    }

    if (
      viewName === 'quiz' &&
      state.quizQuestions.length === 0
    ) {
      loadQuiz();
    }

    if (viewName === 'summary') {
      loadSummaryAndConcepts();
    }
  };

  navItems.forEach(item => {

    item.addEventListener('click', () => {
      switchView(item.dataset.view);
    });

  });

  // =========================================================================
  // 4. DOCUMENT INGESTION & INVENTORY
  // =========================================================================
  const loadDocuments = async () => {

    try {

      const res =
        await fetch('/api/documents');

      const data =
        await res.json();

      state.documents =
        data.documents;

      document.getElementById(
        'stat-docs-count'
      ).textContent =
        data.total_documents;

      document.getElementById(
        'stat-chunks-count'
      ).textContent =
        data.total_chunks;

      document.getElementById(
        'stat-words-count'
      ).textContent =
        data.total_words.toLocaleString();

      document.getElementById(
        'badge-vector-stats'
      ).textContent =
        `${data.total_chunks} Chunks Indexed`;

      const invContainer =
        document.getElementById(
          'document-inventory'
        );

      const docFilterSelect =
        document.getElementById(
          'chat-doc-filter'
        );

      docFilterSelect.innerHTML =
        '<option value="">Search All Uploaded Docs</option>';

      if (data.documents.length === 0) {

        invContainer.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 2rem 0;">
            No documents uploaded yet.
          </div>
        `;

      } else {

        invContainer.innerHTML = '';

        data.documents.forEach(doc => {

          const item =
            document.createElement('div');

          item.className =
            'doc-item';

          item.innerHTML = `
            <div class="doc-info">
              <span class="doc-ext-badge">
                ${doc.ext.toUpperCase()}
              </span>

              <div>
                <div style="font-weight: 600; font-size: 0.92rem;">
                  ${doc.filename}
                </div>

                <div style="font-size: 0.75rem; color: var(--text-muted);">
                  ${doc.chunk_count} chunks • ${doc.word_count} words
                </div>
              </div>
            </div>

            <button
              class="btn-delete-doc icon-btn"
              data-id="${doc.id}"
              style="width: 32px; height: 32px; font-size: 0.85rem; color: #fca5a5;"
              title="Remove document"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          `;

          invContainer.appendChild(item);

          const opt =
            document.createElement('option');

          opt.value = doc.id;
          opt.textContent = doc.filename;

          docFilterSelect.appendChild(opt);
        });

        document
          .querySelectorAll('.btn-delete-doc')
          .forEach(btn => {

            btn.addEventListener(
              'click',
              async (e) => {

                e.stopPropagation();

                const docId =
                  btn.dataset.id;

                await fetch(
                  `/api/documents/${docId}`,
                  {
                    method: 'DELETE'
                  }
                );

                loadDocuments();
              }
            );

          });
      }

    } catch (err) {

      console.error(
        'Failed to load documents:',
        err
      );

    }
  };

  // Upload Handlers

  const dropzone =
    document.getElementById(
      'upload-dropzone'
    );

  const fileInput =
    document.getElementById(
      'file-input'
    );

  const btnBrowse =
    document.getElementById(
      'btn-browse-files'
    );

  const btnLoadSample =
    document.getElementById(
      'btn-load-sample'
    );

  btnBrowse.addEventListener(
    'click',
    () => fileInput.click()
  );

  dropzone.addEventListener(
    'dragover',
    (e) => {

      e.preventDefault();

      dropzone.classList.add(
        'dragover'
      );
    }
  );

  dropzone.addEventListener(
    'dragleave',
    () =>
      dropzone.classList.remove(
        'dragover'
      )
  );

  dropzone.addEventListener(
    'drop',
    (e) => {

      e.preventDefault();

      dropzone.classList.remove(
        'dragover'
      );

      if (
        e.dataTransfer.files.length
      ) {

        uploadFile(
          e.dataTransfer.files[0]
        );
      }
    }
  );

  fileInput.addEventListener(
    'change',
    () => {

      if (fileInput.files.length) {

        uploadFile(
          fileInput.files[0]
        );
      }
    }
  );

  const uploadFile = async (file) => {

    const formData =
      new FormData();

    formData.append(
      'file',
      file
    );

    btnBrowse.disabled = true;

    btnBrowse.innerHTML = `
      <i class="fa-solid fa-spinner fa-spin"></i>
      Processing Vectors...
    `;

    try {

      const res =
        await fetch(
          '/api/upload',
          {
            method: 'POST',
            body: formData
          }
        );

      const data =
        await res.json();

      if (res.ok) {

        alert(data.message);

        loadDocuments();

      } else {

        alert(
          `Error: ${data.detail}`
        );
      }

    } catch (err) {

      alert(
        'Failed to upload file.'
      );

    } finally {

      btnBrowse.disabled = false;

      btnBrowse.innerHTML = `
        <i class="fa-solid fa-folder-open"></i>
        Browse Files
      `;
    }
  };

  btnLoadSample.addEventListener(
    'click',
    async () => {

      btnLoadSample.disabled = true;

      btnLoadSample.innerHTML = `
        <i class="fa-solid fa-spinner fa-spin"></i>
        Indexing...
      `;

      try {

        const res =
          await fetch(
            '/api/load_sample',
            {
              method: 'POST'
            }
          );

        const data =
          await res.json();

        alert(data.message);

        loadDocuments();

      } catch (err) {

        alert(
          'Failed to load sample notes.'
        );

      } finally {

        btnLoadSample.disabled = false;

        btnLoadSample.innerHTML = `
          <i class="fa-solid fa-bolt" style="color: var(--accent-amber);"></i>
          Load Sample RAG Notes
        `;
      }
    }
  );

  loadDocuments();

  // =========================================================================
  // 5. RAG CHAT & QA ENGINE
  // =========================================================================

  const chatThread =
    document.getElementById(
      'chat-thread'
    );

  const chatInput =
    document.getElementById(
      'chat-input-field'
    );

  const btnChatSend =
    document.getElementById(
      'btn-chat-send'
    );

  const docFilterSelect =
    document.getElementById(
      'chat-doc-filter'
    );

  const appendChatMessage = (
    role,
    content,
    citations = []
  ) => {

    const bubble =
      document.createElement('div');

    bubble.className =
      `chat-bubble ${role}`;

    const avatarIcon =
      role === 'user'
        ? 'fa-user'
        : 'fa-atom';

    let citationsHTML = '';

    if (
      citations &&
      citations.length > 0
    ) {

      citationsHTML =
        `<div class="citation-box">`;

      citations.forEach(c => {

        citationsHTML += `
          <span
            class="citation-chip"
            data-snippet="${escapeHTML(c.snippet)}"
          >
            📄 ${c.filename} (Pg ${c.page})
          </span>
        `;
      });

      citationsHTML +=
        `</div>`;
    }

    // ================================================================
    // CLEAN MARKDOWN RENDERER
    // ================================================================

    const formatMarkdown = (text) => {

      if (!text) {
        return '';
      }

      let html =
        escapeHTML(text);

      // Remove legacy wrapper heading
      html =
        html.replace(
          /^#{1,6}\s*💡?\s*\**Alexa['’]s Study Answer\**\s*/im,
          ''
        );

      // Normalize escaped Markdown
      html =
        html.replace(
          /\\([#.*_`>\-])/g,
          '$1'
        );

      // Headings
      html =
        html.replace(
          /^######\s+(.+)$/gm,
          '<h6>$1</h6>'
        );

      html =
        html.replace(
          /^#####\s+(.+)$/gm,
          '<h5>$1</h5>'
        );

      html =
        html.replace(
          /^####\s+(.+)$/gm,
          '<h4>$1</h4>'
        );

      html =
        html.replace(
          /^###\s+(.+)$/gm,
          '<h3>$1</h3>'
        );

      html =
        html.replace(
          /^##\s+(.+)$/gm,
          '<h3>$1</h3>'
        );

      html =
        html.replace(
          /^#\s+(.+)$/gm,
          '<h2>$1</h2>'
        );

      // Bold
      html =
        html.replace(
          /\*\*(.*?)\*\*/g,
          '<strong>$1</strong>'
        );

      // Italic
      html =
        html.replace(
          /(?<!\*)\*([^*]+)\*(?!\*)/g,
          '<em>$1</em>'
        );

      // Inline code
      html =
        html.replace(
          /`([^`]+)`/g,
          '<code>$1</code>'
        );

      // Markdown links
      html =
        html.replace(
          /\[([^\]]+)\]\(([^)]+)\)/g,
          '$1'
        );

      // Blockquotes
      html =
        html.replace(
          /^>\s*(.+)$/gm,
          '<blockquote>$1</blockquote>'
        );

      // Horizontal rules
      html =
        html.replace(
          /^\s*---+\s*$/gm,
          ''
        );

      // Bullet points
      html =
        html.replace(
          /^\s*[-*•]\s+(.+)$/gm,
          '<li>$1</li>'
        );

      // Numbered lists
      html =
        html.replace(
          /^\s*\d+[.)]\s+(.+)$/gm,
          '<li>$1</li>'
        );

      // Group consecutive list items
      html =
        html.replace(
          /((?:<li>.*?<\/li>\s*)+)/gs,
          '<ul>$1</ul>'
        );

      // Paragraph spacing
      html =
        html.replace(
          /\n{3,}/g,
          '\n\n'
        );

      html =
        html.replace(
          /\n/g,
          '<br>'
        );

      return html;
    };

    const formattedText =
      formatMarkdown(content);

    bubble.innerHTML = `
      <div class="chat-avatar">
        <i class="fa-solid ${avatarIcon}"></i>
      </div>

      <div class="chat-content">
        ${formattedText}
        ${citationsHTML}
      </div>
    `;

    chatThread.appendChild(
      bubble
    );

    chatThread.scrollTop =
      chatThread.scrollHeight;

    bubble
      .querySelectorAll(
        '.citation-chip'
      )
      .forEach(chip => {

        chip.addEventListener(
          'click',
          () => {

            alert(
              `Source Excerpt:\n\n"${chip.dataset.snippet}"`
            );

          }
        );

      });
  };

  // ================================================================
  // VOICE QUERY FLAG
  //
  // Typed question:
  // sendQuery(question)
  //
  // Voice question:
  // sendQuery(question, true)
  //
  // Only voice questions trigger TTS.
  // ================================================================

  const sendQuery = async (
    queryText,
    isVoiceQuery = false
  ) => {

    if (!queryText.trim()) {
      return;
    }

    appendChatMessage(
      'user',
      queryText
    );

    chatInput.value = '';

    const loadingId =
      'loading-' + Date.now();

    const loadingBubble =
      document.createElement('div');

    loadingBubble.className =
      'chat-bubble bot';

    loadingBubble.id =
      loadingId;

    loadingBubble.innerHTML = `
      <div class="chat-avatar">
        <i class="fa-solid fa-atom"></i>
      </div>

      <div
        class="chat-content"
        style="display: flex; align-items: center; gap: 0.5rem;"
      >
        <i
          class="fa-solid fa-spinner fa-spin"
          style="color: var(--accent-cyan);"
        ></i>

        Searching vector index & synthesizing response...
      </div>
    `;

    chatThread.appendChild(
      loadingBubble
    );

    chatThread.scrollTop =
      chatThread.scrollHeight;

    try {

      const res =
        await fetch(
          '/api/chat',
          {
            method: 'POST',

            headers: {
              'Content-Type':
                'application/json'
            },

            body: JSON.stringify({
              query: queryText,
              doc_id:
                docFilterSelect.value ||
                null
            })
          }
        );

      const data =
        await res.json();

      document
        .getElementById(
          loadingId
        )
        ?.remove();

      appendChatMessage(
        'bot',
        data.answer,
        data.citations
      );

      // ONLY voice queries trigger speech
      if (isVoiceQuery) {
        speakText(data.answer);
      }

    } catch (err) {

      document
        .getElementById(
          loadingId
        )
        ?.remove();

      appendChatMessage(
        'bot',
        'Sorry, an error occurred while searching your study documents.'
      );
    }
  };

  // Typed questions remain silent.

  btnChatSend.addEventListener(
    'click',
    () => {
      sendQuery(
        chatInput.value
      );
    }
  );

  chatInput.addEventListener(
    'keydown',
    (e) => {

      if (e.key === 'Enter') {

        sendQuery(
          chatInput.value
        );
      }

    }
  );

  // =========================================================================
  // 6. FLASHCARDS SYSTEM
  // =========================================================================

  const cardElement =
    document.getElementById(
      'flashcard-element'
    );

  const cardQText =
    document.getElementById(
      'card-q-text'
    );

  const cardAText =
    document.getElementById(
      'card-a-text'
    );

  const cardCounter =
    document.getElementById(
      'card-counter'
    );

  const btnFlipCard =
    document.getElementById(
      'btn-flip-card'
    );

  const btnPrevCard =
    document.getElementById(
      'btn-prev-card'
    );

  const btnNextCard =
    document.getElementById(
      'btn-next-card'
    );

  const btnRefreshCards =
    document.getElementById(
      'btn-refresh-cards'
    );

  const loadFlashcards =
    async () => {

      try {

        const res =
          await fetch(
            '/api/flashcards?count=6'
          );

        const data =
          await res.json();

        state.flashcards =
          data.flashcards;

        state.currentCardIndex =
          0;

        renderCurrentCard();

      } catch (err) {

        console.error(
          'Failed to load flashcards:',
          err
        );
      }
    };

  const renderCurrentCard =
    () => {

      if (
        !state.flashcards.length
      ) {
        return;
      }

      cardElement.classList.remove(
        'flipped'
      );

      setTimeout(() => {

        const card =
          state.flashcards[
            state.currentCardIndex
          ];

        cardQText.innerHTML =
          card.question.replace(
            /\*\*(.*?)\*\*/g,
            '<strong>$1</strong>'
          );

        cardAText.textContent =
          card.answer;

        cardCounter.textContent =
          `Card ${
            state.currentCardIndex + 1
          } of ${
            state.flashcards.length
          }`;

      }, 200);
    };

  cardElement.addEventListener(
    'click',
    () =>
      cardElement.classList.toggle(
        'flipped'
      )
  );

  btnFlipCard.addEventListener(
    'click',
    () =>
      cardElement.classList.toggle(
        'flipped'
      )
  );

  btnNextCard.addEventListener(
    'click',
    () => {

      if (
        state.currentCardIndex <
        state.flashcards.length - 1
      ) {

        state.currentCardIndex++;

        renderCurrentCard();
      }
    }
  );

  btnPrevCard.addEventListener(
    'click',
    () => {

      if (
        state.currentCardIndex > 0
      ) {

        state.currentCardIndex--;

        renderCurrentCard();
      }
    }
  );

  btnRefreshCards.addEventListener(
    'click',
    loadFlashcards
  );

  // =========================================================================
  // 7. AI QUIZ STUDIO
  // =========================================================================

  const quizTitle =
    document.getElementById(
      'quiz-question-title'
    );

  const quizNum =
    document.getElementById(
      'quiz-question-num'
    );

  const quizScoreVal =
    document.getElementById(
      'quiz-score-val'
    );

  const quizOptionsContainer =
    document.getElementById(
      'quiz-options-container'
    );

  const quizExpBox =
    document.getElementById(
      'quiz-explanation-box'
    );

  const quizExpText =
    document.getElementById(
      'quiz-explanation-text'
    );

  const btnNextQuestion =
    document.getElementById(
      'btn-next-question'
    );

  const loadQuiz =
    async () => {

      try {

        const res =
          await fetch(
            '/api/quiz?count=4'
          );

        const data =
          await res.json();

        state.quizQuestions =
          data.quiz;

        state.currentQuizIndex =
          0;

        state.quizScore =
          0;

        quizScoreVal.textContent =
          '0';

        renderCurrentQuiz();

      } catch (err) {

        console.error(
          'Failed to load quiz:',
          err
        );
      }
    };

  const renderCurrentQuiz =
    () => {

      if (
        !state.quizQuestions.length
      ) {
        return;
      }

      quizExpBox.style.display =
        'none';

      const q =
        state.quizQuestions[
          state.currentQuizIndex
        ];

      quizNum.textContent =
        `Question ${
          state.currentQuizIndex + 1
        } of ${
          state.quizQuestions.length
        }`;

      quizTitle.innerHTML =
        q.question.replace(
          /\*\*(.*?)\*\*/g,
          '<strong>$1</strong>'
        );

      quizOptionsContainer.innerHTML =
        '';

      q.options.forEach(
        (opt, idx) => {

          const btn =
            document.createElement(
              'button'
            );

          btn.className =
            'option-btn';

          btn.innerHTML = `
            <span
              style="
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: rgba(255,255,255,0.1);
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 0.85rem;
                font-weight: 700;
              "
            >
              ${String.fromCharCode(
                65 + idx
              )}
            </span>

            ${opt}
          `;

          btn.addEventListener(
            'click',
            () =>
              handleQuizOptionClick(
                idx,
                q.correct,
                btn,
                q.explanation
              )
          );

          quizOptionsContainer.appendChild(
            btn
          );
        }
      );
    };

  const handleQuizOptionClick =
    (
      selectedIdx,
      correctIdx,
      btnElement,
      explanation
    ) => {

      const optionBtns =
        quizOptionsContainer
          .querySelectorAll(
            '.option-btn'
          );

      optionBtns.forEach(
        b =>
          b.disabled = true
      );

      if (
        selectedIdx === correctIdx
      ) {

        btnElement.classList.add(
          'selected-correct'
        );

        state.quizScore += 100;

        quizScoreVal.textContent =
          state.quizScore;

      } else {

        btnElement.classList.add(
          'selected-wrong'
        );

        optionBtns[
          correctIdx
        ].classList.add(
          'selected-correct'
        );
      }

      quizExpText.textContent =
        explanation;

      quizExpBox.style.display =
        'block';
    };

  btnNextQuestion.addEventListener(
    'click',
    () => {

      if (
        state.currentQuizIndex <
        state.quizQuestions.length - 1
      ) {

        state.currentQuizIndex++;

        renderCurrentQuiz();

      } else {

        alert(
          `Quiz Finished! Your final score is ${state.quizScore} points.`
        );

        loadQuiz();
      }
    }
  );

  // =========================================================================
  // 8. ALEXA VOICE HUB & STT/TTS
  // =========================================================================

  const btnMicToggle =
    document.getElementById(
      'btn-mic-toggle'
    );

  const sidebarVoiceTrigger =
    document.getElementById(
      'sidebar-voice-trigger'
    );

  const btnStartVoice =
    document.getElementById(
      'btn-start-voice-session'
    );

  const btnStopVoice =
    document.getElementById(
      'btn-stop-voice-session'
    );

  const voiceStatusText =
    document.getElementById(
      'voice-status-text'
    );

  // =========================================================================
  // SPEECH RECOGNITION
  // =========================================================================

  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  if (SpeechRecognition) {

    state.recognition =
      new SpeechRecognition();

    state.recognition.continuous =
      false;

    state.recognition.interimResults =
      false;

    state.recognition.lang =
      'en-US';

    state.recognition.onstart =
      () => {

        state.isListening =
          true;

        btnMicToggle.classList.add(
          'recording'
        );

        voiceStatusText.textContent =
          '🎙️ Listening to your voice... Speak now!';
      };

    state.recognition.onresult =
      (event) => {

        const transcript =
          event.results[0][0]
            .transcript;

        voiceStatusText.textContent =
          `Recognized: "${transcript}"`;

        switchView('chat');

        // true = this came from voice
        sendQuery(
          transcript,
          true
        );
      };

    state.recognition.onerror =
      () => {

        voiceStatusText.textContent =
          'Voice recognition error. Try again.';

        btnMicToggle.classList.remove(
          'recording'
        );

        state.isListening =
          false;
      };

    state.recognition.onend =
      () => {

        btnMicToggle.classList.remove(
          'recording'
        );

        state.isListening =
          false;
      };
  }

  const toggleVoiceInput =
    () => {

      if (!state.recognition) {

        alert(
          'Speech Recognition is not supported by your browser.'
        );

        return;
      }

      if (state.isListening) {

        state.recognition.stop();

      } else {

        state.recognition.start();
      }
    };

  btnMicToggle.addEventListener(
    'click',
    toggleVoiceInput
  );

  sidebarVoiceTrigger.addEventListener(
    'click',
    () => {

      switchView('voice');

      toggleVoiceInput();
    }
  );

  if (btnStartVoice) {

    btnStartVoice.addEventListener(
      'click',
      toggleVoiceInput
    );
  }

  if (btnStopVoice) {

    btnStopVoice.addEventListener(
      'click',
      () =>
        state.recognition?.stop()
    );
  }

  // =========================================================================
  // TEXT TO SPEECH
  // =========================================================================

  const cleanMarkdownForSpeech =
    (rawText) => {

      if (!rawText) {
        return '';
      }

      return rawText

        // Remove Markdown headings
        .replace(
          /^#{1,6}\s*/gm,
          ''
        )

        // Remove bold
        .replace(
          /\*\*(.*?)\*\*/g,
          '$1'
        )

        // Remove italic
        .replace(
          /(?<!\*)\*([^*]+)\*(?!\*)/g,
          '$1'
        )

        // Remove inline code
        .replace(
          /`([^`]+)`/g,
          '$1'
        )

        // Markdown links
        .replace(
          /\[([^\]]+)\]\([^)]+\)/g,
          '$1'
        )

        // URLs
        .replace(
          /https?:\/\/\S+/g,
          ''
        )

        // Blockquotes
        .replace(
          /^\s*>\s?/gm,
          ''
        )

        // Bullets
        .replace(
          /^\s*[-*•]\s+/gm,
          ''
        )

        // Numbered lists
        .replace(
          /^\s*\d+[.)]\s+/gm,
          ''
        )

        // Horizontal rules
        .replace(
          /^\s*---+\s*$/gm,
          ''
        )

        // Citation brackets
        .replace(
          /\[[^\]]*\]/g,
          ''
        )

        // Escaped Markdown
        .replace(
          /\\([#.*_`>\-])/g,
          '$1'
        )

        // New lines
        .replace(
          /[\n\r]+/g,
          '. '
        )

        // Spaces
        .replace(
          /\s+/g,
          ' '
        )

        .replace(
          /\.{2,}/g,
          '.'
        )

        .trim();
    };

  const getShortSpeechText =
    (rawText) => {

      let text =
        cleanMarkdownForSpeech(
          rawText
        );

      if (!text) {
        return '';
      }

      // Remove UI labels from speech
      text =
        text
          .replace(
            /Alexa['’]s Study Answer[:.]?/gi,
            ''
          )
          .replace(
            /Key Context Breakdown[:.]?/gi,
            ''
          )
          .replace(
            /Sources? verified.*$/gi,
            ''
          )
          .trim();

      // Get complete sentences
      const sentences =
        text.match(
          /[^.!?]+[.!?]+/g
        );

      // Speak only first two sentences
      if (
        sentences &&
        sentences.length > 0
      ) {

        text =
          sentences
            .slice(0, 2)
            .join(' ')
            .trim();
      }

      const MAX_SPEECH_LENGTH =
        280;

      if (
        text.length >
        MAX_SPEECH_LENGTH
      ) {

        text =
          text.substring(
            0,
            MAX_SPEECH_LENGTH
          );

        const lastSpace =
          text.lastIndexOf(' ');

        if (
          lastSpace > 180
        ) {

          text =
            text.substring(
              0,
              lastSpace
            );
        }

        text += '.';
      }

      return text;
    };

  const speakText =
    (text) => {

      if (
        !state.synth ||
        !text
      ) {
        return;
      }

      state.synth.cancel();

      const shortText =
        getShortSpeechText(
          text
        );

      if (!shortText) {
        return;
      }

      console.log(
        'Alexa speaking:',
        shortText
      );

      const utterance =
        new SpeechSynthesisUtterance(
          shortText
        );

      utterance.rate =
        0.95;

      utterance.pitch =
        1.0;

      utterance.volume =
        1.0;

      state.synth.speak(
        utterance
      );
    };

  // =========================================================================
  // 9. ANALYTICS & SUMMARY LOADER
  // =========================================================================

  const loadSummaryAndConcepts =
    async () => {

      const summaryContainer =
        document.getElementById(
          'summary-content'
        );

      const takeawaysList =
        document.getElementById(
          'takeaways-list'
        );

      const conceptsContainer =
        document.getElementById(
          'concepts-tag-cloud'
        );

      try {

        const [
          sumRes,
          conRes
        ] = await Promise.all([

          fetch(
            '/api/summarize'
          ),

          fetch(
            '/api/concepts'
          )
        ]);

        const sumData =
          await sumRes.json();

        const conData =
          await conRes.json();

        summaryContainer.innerHTML =
          sumData.executive_summary
            .replace(
              /\n\n/g,
              '<br><br>'
            );

        takeawaysList.innerHTML =
          '';

        sumData.key_takeaways
          .forEach(t => {

            const li =
              document.createElement(
                'li'
              );

            li.textContent =
              t;

            takeawaysList.appendChild(
              li
            );
          });

        conceptsContainer.innerHTML =
          '';

        conData.concepts
          .forEach(c => {

            const tag =
              document.createElement(
                'div'
              );

            tag.className =
              'concept-tag';

            tag.innerHTML =
              `${c.name} <span>${c.frequency}</span>`;

            conceptsContainer.appendChild(
              tag
            );
          });

      } catch (err) {

        console.error(
          'Failed to load summary analytics:',
          err
        );
      }
    };

  // =========================================================================
  // 10. SETTINGS HANDLER
  // =========================================================================

  const btnSaveSettings =
    document.getElementById(
      'btn-save-settings'
    );

  const inputGeminiKey =
    document.getElementById(
      'input-gemini-key'
    );

  btnSaveSettings.addEventListener(
    'click',
    async () => {

      const key =
        inputGeminiKey.value;

      try {

        const res =
          await fetch(
            '/api/settings',
            {
              method: 'POST',

              headers: {
                'Content-Type':
                  'application/json'
              },

              body: JSON.stringify({
                api_key: key
              })
            }
          );

        const data =
          await res.json();

        alert(
          data.message
        );

      } catch (err) {

        alert(
          'Failed to save settings.'
        );
      }
    }
  );

  // =========================================================================
  // HELPER
  // =========================================================================

  const escapeHTML =
    (str) => {

      return str.replace(
        /[&<>'"]/g,

        tag =>
          ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
          }[tag] || tag)
      );
    };

});