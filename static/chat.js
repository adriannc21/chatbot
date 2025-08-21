// Estado global mínimo
let currentStep = "info";
let currentCategoria = null;
let dataTree = null;
let sessionId = null;

// Generar o recuperar sessionId
function getOrCreateSessionId() {
  let storedSessionId = sessionStorage.getItem("fabrix_session_id");
  if (!storedSessionId) {
    storedSessionId =
      "fabrix_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem("fabrix_session_id", storedSessionId);
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
  sessionId = getOrCreateSessionId();

  const content = document.querySelector("#chatbotFabrix #fabrixContent");
  const activ = document.querySelector("#fabrixToggle");
  const closeBtn = document.querySelector("#chatbotFabrix .top .out");
  const faqButton = document.querySelector(
    "#chatbotFabrix .help.questions .btn-in"
  );
  const returnBtn = document.querySelector("#chatbotFabrix .top .return");
  const info = document.querySelector("#chatbotFabrix .info");
  const tree = document.querySelector("#chatbotFabrix .tree");
  const flow = document.querySelector("#chatbotFabrix .top .flow");
  const recButton = document.querySelector(
    "#chatbotFabrix .help.product .btn-in"
  );
  const recChat = document.querySelector("#chatbotFabrix .recommendation-chat");
  const helpBtn = document.querySelector(
    "#chatbotFabrix .content .info .help .btn-in"
  );

  if (activ) activ.addEventListener("click", toggleFabrixChat);

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      content.classList.remove("show", "chatopen");
      const activDiv = document.querySelector("#chatbotFabrix .activ");
      if (activDiv) activDiv.style.display = "flex";
    });
  }

  if (faqButton) faqButton.addEventListener("click", cargarArbolPreguntas);

  if (returnBtn) {
    returnBtn.addEventListener("click", function () {
      if (recChat.style.display === "flex") {
        recChat.style.display = "none";
        info.style.display = "flex";
        returnBtn.style.display = "none";
        flow.style.display = "flex";
        currentStep = "info";
        content.classList.remove("chatopen");
        return;
      }
      if (currentStep === "preguntas") {
        renderCategorias(dataTree, tree);
        currentStep = "categorias";
      } else if (currentStep === "respuesta") {
        renderPreguntas(
          currentCategoria,
          dataTree[currentCategoria],
          tree,
          dataTree
        );
        currentStep = "preguntas";
      } else {
        tree.style.display = "none";
        info.style.display = "flex";
        returnBtn.style.display = "none";
        flow.style.display = "flex";
        currentStep = "info";
        content.classList.remove("chatopen");
      }
    });
  }

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

  if (helpBtn) {
    helpBtn.addEventListener("click", () => {
      content.classList.add("show", "chatopen");
    });
  }
});

function initChatInterface() {
  const chatResponse = document.getElementById("chatResponse");
  const sendBtn = document.getElementById("sendQuestion");
  const userQuestion = document.getElementById("userQuestion");

  const addMsg = (content, cls = "bot") => {
    const msg = document.createElement("div");
    msg.className = `chat-bubble ${cls}`;
    if (typeof content === "string") msg.innerHTML = content;
    else msg.appendChild(content);
    chatResponse.appendChild(msg);
    chatResponse.scrollTop = chatResponse.scrollHeight;
  };

  const createProductCard = (producto) => {
    const card = document.createElement("a");
    card.className = "producto-card";
    card.href = producto.enlace;
    card.target = "_blank";
    card.rel = "noopener";

    card.innerHTML = `
    <img class="image" src="${producto.imagen}" alt="${producto.nombre}" />
    <div class="dats">
      <span class="name">
        ${producto.nombre}
      </span>
      <p class="price">
        ${producto.precio}
      </p>
    </div>
  `;
    return card;
  };

  addMsg(
    "👋 ¡Hola! Soy Fabrix, tu asistente virtual. ¿En qué puedo ayudarte hoy?"
  );

  userQuestion.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  sendBtn.addEventListener("click", async () => {
    const question = userQuestion.value.trim();
    if (!question) return;

    // Guardamos el contenido original del botón para restaurarlo después
    const originalContent = sendBtn.innerHTML;

    // Mostrar "..." y deshabilitar
    sendBtn.disabled = true;
    sendBtn.textContent = "...";

    // Agregar mensaje del usuario
    addMsg(question, "user");
    userQuestion.value = "";

    // Animación de loading en chat
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

    try {
      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify({ message: question, session_id: sessionId }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      loading.remove();

      // Actualizar sessionId si cambió
      if (data.session_id && data.session_id !== sessionId) {
        sessionId = data.session_id;
        sessionStorage.setItem("fabrix_session_id", sessionId);
      }

      if (data.respuesta) addMsg(data.respuesta);
      if (data.mostrar_productos && Array.isArray(data.productos)) {
        // Crear un contenedor único para todos los productos
        const productsContainer = document.createElement("div");
        productsContainer.className = "chat-bubble bot bot-products"; // clase extra

        // Agregar todas las tarjetas al contenedor
        data.productos.forEach((producto) => {
          const card = createProductCard(producto);
          productsContainer.appendChild(card);
        });

        // Añadir contenedor al chat
        chatResponse.appendChild(productsContainer);
        chatResponse.scrollTop = chatResponse.scrollHeight;
      }
      if (!data.respuesta && (!data.productos || data.productos.length === 0)) {
        addMsg(
          "No encontré información relacionada con tu consulta. ¿Puedes ser más específico?"
        );
      }
    } catch (err) {
      loading.remove();
      console.error(err);
      addMsg(
        "❌ Error al conectar con el servidor. Por favor, intenta nuevamente."
      );
    } finally {
      // Restaurar botón original
      sendBtn.disabled = false;
      sendBtn.innerHTML = originalContent;
      userQuestion.focus();
    }
  });
}

/* ===== FAQ ===== */
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
    dataTree = result.data;
    renderCategorias(dataTree, container);
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
