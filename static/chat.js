// Estado global mínimo
let currentStep = "info";
let currentCategoria = null;
let dataTree = null;
let sessionId = null;

// Generar o recuperar sessionId
function getOrCreateSessionId() {
  let storedSessionId = sessionStorage.getItem('fabrix_session_id');
  if (!storedSessionId) {
    storedSessionId = 'fabrix_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem('fabrix_session_id', storedSessionId);
  }
  return storedSessionId;
}

function toggleFabrixChat() {
  const content = document.querySelector("#chatbotFabrix #fabrixContent");
  const activ = document.querySelector("#chatbotFabrix .activ");

  content.classList.toggle("show");
  activ.style.display = content.classList.contains("show") ? "none" : "flex";
}

document.addEventListener("DOMContentLoaded", function () {
  // Inicializar sessionId al cargar
  sessionId = getOrCreateSessionId();
  
  const content = document.querySelector("#chatbotFabrix #fabrixContent");
  const activ = document.querySelector("#fabrixToggle");
  const closeBtn = document.querySelector("#chatbotFabrix .top .out");
  const faqButton = document.querySelector("#chatbotFabrix .help.questions .btn-in");
  const returnBtn = document.querySelector("#chatbotFabrix .top .return");
  const info = document.querySelector("#chatbotFabrix .info");
  const tree = document.querySelector("#chatbotFabrix .tree");
  const flow = document.querySelector("#chatbotFabrix .top .flow");
  const recButton = document.querySelector("#chatbotFabrix .help.product .btn-in");
  const recChat = document.querySelector("#chatbotFabrix .recommendation-chat");

  // Toggle del launcher
  if (activ) activ.addEventListener("click", toggleFabrixChat);

  // Cerrar
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      content.classList.remove("show");
      const activDiv = document.querySelector("#chatbotFabrix .activ");
      if (activDiv) activDiv.style.display = "flex";
    });
  }

  // FAQ
  if (faqButton) faqButton.addEventListener("click", cargarArbolPreguntas);

  // Botón volver
  if (returnBtn) {
    returnBtn.addEventListener("click", function () {
      if (recChat.style.display === "flex") {
        recChat.style.display = "none";
        info.style.display = "flex";
        returnBtn.style.display = "none";
        flow.style.display = "flex";
        currentStep = "info";
        return;
      }
      if (currentStep === "preguntas") {
        renderCategorias(dataTree, tree);
        currentStep = "categorias";
      } else if (currentStep === "respuesta") {
        renderPreguntas(currentCategoria, dataTree[currentCategoria], tree, dataTree);
        currentStep = "preguntas";
      } else {
        tree.style.display = "none";
        info.style.display = "flex";
        returnBtn.style.display = "none";
        flow.style.display = "flex";
        currentStep = "info";
      }
    });
  }

  /* ========== Ver opciones recomendadas ========== */
  if (recButton) {
    recButton.addEventListener("click", () => {
      info.style.display = "none";
      tree.style.display = "none";
      recChat.style.display = "flex";
      returnBtn.style.display = "flex";
      flow.style.display = "none";
      currentStep = "recommendation";

      initChatInterface();
    });
  }
});

function initChatInterface() {
  const recChat = document.querySelector("#chatbotFabrix .recommendation-chat");
  
  recChat.innerHTML = `
    <div id="chatResponse" 
        style="display:flex;flex-direction:column;gap:0.5rem;background:#ffffff; padding:0.5rem; border-radius:6px; min-height:150px; max-height:350px; overflow-y:auto; margin-bottom:0.5rem;">
    </div>
    <div style="display:flex; gap:0.5rem; align-items:flex-end;">
      <textarea id="userQuestion" placeholder="Escribe tu consulta aquí..." rows="3" 
                style="outline: none; font-family: 'Poppins';flex:1; resize:none; padding:0.5rem; border:1px solid #ddd; border-radius:8px;"></textarea>
      <button id="sendQuestion" style="cursor:pointer; font-size: .9rem; padding:0.5rem 0.75rem; border-radius:8px; border: 1px solid #ff8018; background:#ea7134; color:#fff; white-space:nowrap;">Enviar</button>
    </div>
  `;

  const chatResponse = document.getElementById("chatResponse");
  const sendBtn = document.getElementById("sendQuestion");
  const userQuestion = document.getElementById("userQuestion");

  const addMsg = (content, cls = "bot") => {
    const msg = document.createElement("div");
    msg.className = `chat-bubble ${cls}`;
    
    if (typeof content === 'string') {
      msg.innerHTML = content;
    } else {
      msg.appendChild(content);
    }
    
    chatResponse.appendChild(msg);
    chatResponse.scrollTop = chatResponse.scrollHeight;
  };

  const createProductCard = (producto) => {
    const card = document.createElement("div");
    card.className = "producto-card";
    card.style.cssText = `
      display: flex;
      gap: 0.75rem;
      border-radius: 8px;
      padding: 0.75rem;
      margin: 0.25rem 0;
      transition: all 0.2s ease;
    `;
    
    card.innerHTML = `
      <img src="${producto.imagen}" alt="${producto.nombre}" 
           style="width: 80px; height: 80px; object-fit: cover; border-radius: 6px; flex-shrink: 0;" />
      <div style="flex: 1; display: flex; flex-direction: column; gap: 0.25rem;">
        <a href="${producto.enlace}" target="_blank" rel="noopener" 
           style="font-weight: 600; color: #ea7134; text-decoration: none; font-size: 0.9rem; line-height: 1.2;">
          ${producto.nombre}
        </a>
        <p style="font-weight: 700; color: #28a745; margin: 0; font-size: 1rem;">
          ${producto.precio}
        </p>
      </div>
    `;

    // Hover effect
    card.addEventListener('mouseenter', () => {
      card.style.borderColor = '#ff8018';
      card.style.boxShadow = '0 2px 8px rgba(255,128,24,0.15)';
    });
    
    card.addEventListener('mouseleave', () => {
      card.style.borderColor = '#e9ecef';
      card.style.boxShadow = 'none';
    });

    return card;
  };

  // Mensaje de bienvenida
  addMsg("👋 ¡Hola! Soy Fabrix, tu asistente virtual. ¿En qué puedo ayudarte hoy?");

  // Enviar con Enter
  userQuestion.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // Enviar pregunta
  sendBtn.addEventListener("click", async () => {
    const question = userQuestion.value.trim();
    if (!question) return;

    // Deshabilitar envío
    sendBtn.disabled = true;
    sendBtn.textContent = "...";

    // Mostrar mensaje del usuario
    addMsg(question, "user");
    userQuestion.value = "";

    // Loading
    const loading = document.createElement("div");
    loading.className = "chat-bubble bot";
    loading.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <div style="width: 12px; height: 12px; border: 2px solid #ff8018; border-top: 2px solid transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        Buscando opciones para ti...
      </div>
    `;
    chatResponse.appendChild(loading);
    chatResponse.scrollTop = chatResponse.scrollHeight;

    // Agregar CSS para la animación si no existe
    if (!document.getElementById('spin-animation')) {
      const style = document.createElement('style');
      style.id = 'spin-animation';
      style.textContent = `
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }

    try {
      const res = await fetch("https://5f8853f706af.ngrok-free.app/chat", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify({
          message: question,
          session_id: sessionId,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      loading.remove();

      // Actualizar sessionId si es necesario
      if (data.session_id && data.session_id !== sessionId) {
        sessionId = data.session_id;
        sessionStorage.setItem('fabrix_session_id', sessionId);
      }

      // Mostrar respuesta del asistente
      if (data.respuesta) {
        addMsg(data.respuesta);
      }

      // Mostrar productos solo si el backend indica que debe hacerlo
      if (data.mostrar_productos && Array.isArray(data.productos) && data.productos.length > 0) {
        data.productos.forEach(producto => {
          const productCard = createProductCard(producto);
          addMsg(productCard);
        });
      }

      if (!data.respuesta && (!data.productos || data.productos.length === 0)) {
        addMsg("No encontré información relacionada con tu consulta. ¿Puedes ser más específico?");
      }

    } catch (err) {
      loading.remove();
      console.error('Error:', err);
      addMsg("❌ Error al conectar con el servidor. Por favor, intenta nuevamente.");
    } finally {
      // Reactivar envío
      sendBtn.disabled = false;
      sendBtn.textContent = "Enviar";
      userQuestion.focus();
    }
  });
}

/* ====== FAQ helpers (sin cambios) ====== */
async function cargarArbolPreguntas() {
  const container = document.querySelector("#chatbotFabrix .tree");
  const info = document.querySelector("#chatbotFabrix .info");
  const returnBtn = document.querySelector("#chatbotFabrix .top .return");
  const flow = document.querySelector("#chatbotFabrix .top .flow");

  container.innerHTML = "<p>Cargando preguntas...</p>";
  info.style.display = "none";
  container.style.display = "flex";
  returnBtn.style.display = "flex";
  flow.style.display = "none";
  currentStep = "categorias";

  try {
    const response = await fetch("https://api.krear3d.com/general/questions");
    const result = await response.json();
    const data = result.data;
    dataTree = data;
    renderCategorias(data, container);
  } catch (error) {
    container.innerHTML = "<p>Error al cargar preguntas frecuentes.</p>";
    console.error(error);
  }
}

function renderCategorias(data, container) {
  const flow = document.querySelector("#chatbotFabrix .top .flow");
  flow.style.display = "none";
  container.innerHTML = "<p class='tit'>Categorías:</p>";
  Object.keys(data).forEach((categoria) => {
    const btn = document.createElement("button");
    btn.className = "btn-in";
    btn.innerHTML = `${categoria} <img class='icon-right' src="https://dev.tiendakrear3d.com/wp-content/uploads/2025/06/right.webp" alt="Ir" />`;
    btn.onclick = () => {
      currentCategoria = categoria;
      renderPreguntas(categoria, data[categoria], container, data);
      currentStep = "preguntas";
    };
    container.appendChild(btn);
  });
}

function renderPreguntas(categoria, preguntas, container, data) {
  container.innerHTML = `<p><strong class='subt'>${categoria}</strong></p>`;
  preguntas.forEach(({ pregunta, respuesta }) => {
    const btn = document.createElement("button");
    btn.className = "btn-in";
    btn.innerHTML = `${pregunta} <img class='icon-right' src="https://dev.tiendakrear3d.com/wp-content/uploads/2025/06/right.webp" alt="Ver" />`;
    btn.onclick = () => {
      mostrarRespuesta(pregunta, respuesta, container);
      currentStep = "respuesta";
    };
    container.appendChild(btn);
  });
}

function mostrarRespuesta(pregunta, respuesta, container) {
  container.innerHTML = `
    <p><strong class='subt'>${pregunta}</strong></p>
    <p>${respuesta}</p>
  `;
}