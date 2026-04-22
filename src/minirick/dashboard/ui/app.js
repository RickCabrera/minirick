/* minirick dashboard — frontend logic (vanilla, no framework) */

(function () {
  'use strict';

  const STATE_IDS = ['state-loading', 'state-error', 'state-empty', 'state-task'];

  function showState(stateId) {
    for (const id of STATE_IDS) {
      const el = document.getElementById(id);
      if (el) el.hidden = id !== stateId;
    }
  }

  function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => t.classList.add('hidden'), 3000);
  }

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderMarkdown(md) {
    if (!md) return '<em class="dim">(sin contexto)</em>';
    if (typeof marked !== 'undefined' && marked.parse) {
      try {
        return marked.parse(md);
      } catch (e) {
        // fallthrough to pre
      }
    }
    return '<pre>' + escapeHtml(md) + '</pre>';
  }

  function renderStatusBadge(status) {
    const safe = String(status || 'todo').toLowerCase();
    const known = ['todo', 'in_progress', 'done'];
    const cls = known.includes(safe) ? 'status-' + safe : '';
    return '<span class="status-badge ' + cls + '">[' + escapeHtml(safe) + ']</span>';
  }

  function toolDetail(tool) {
    if (tool.url) return tool.url;
    if (tool.path) return tool.path;
    if (tool.cwd) return tool.cwd;
    if (tool.content) return '(inline content)';
    return '';
  }

  function renderTools(tools) {
    if (!tools || tools.length === 0) {
      return '<div class="empty-inline">(sin herramientas)</div>';
    }
    return tools
      .map(function (tool, idx) {
        return (
          '<div class="tool" data-index="' +
          idx +
          '">' +
          '<span class="tool-type">' +
          escapeHtml(tool.type) +
          '</span>' +
          '<span class="tool-detail">' +
          escapeHtml(toolDetail(tool)) +
          '</span>' +
          '</div>'
        );
      })
      .join('');
  }

  function renderTask(task) {
    const titleEl = document.getElementById('task-title');
    const statusEl = document.getElementById('task-status');
    const summaryEl = document.getElementById('task-summary');
    const contextEl = document.getElementById('task-context');
    const toolsEl = document.getElementById('task-tools');
    const toolsCountEl = document.getElementById('tools-count');

    if (titleEl) titleEl.textContent = task.title || '(sin título)';
    if (statusEl) statusEl.innerHTML = renderStatusBadge(task.status);
    if (summaryEl) summaryEl.textContent = task.summary || '(sin resumen)';
    if (contextEl) contextEl.innerHTML = renderMarkdown(task.context_md);
    if (toolsEl) toolsEl.innerHTML = renderTools(task.tools);
    if (toolsCountEl) toolsCountEl.textContent = (task.tools || []).length;

    // Wire tool clicks
    document.querySelectorAll('.tool').forEach(function (el) {
      el.addEventListener('click', function () {
        const idx = parseInt(el.getAttribute('data-index'), 10);
        window.pywebview.api
          .open_tool(idx)
          .then(function (r) {
            if (r && (r.message || r.error)) {
              showToast(r.message || r.error);
            }
          })
          .catch(function (e) {
            showToast('Error: ' + e);
          });
      });
    });
  }

  function renderProfile(profile) {
    const emailEl = document.getElementById('footer-email');
    const roleEl = document.getElementById('footer-role');
    const avatarEl = document.getElementById('avatar-initial');

    if (!profile) {
      if (emailEl) emailEl.textContent = '(sin sesión)';
      if (roleEl) roleEl.textContent = '';
      if (avatarEl) avatarEl.textContent = '?';
      return;
    }

    const email = profile.email || '';
    const role = profile.role || '';

    if (emailEl) emailEl.textContent = email;
    if (roleEl) roleEl.textContent = role;
    if (avatarEl) avatarEl.textContent = email.length > 0 ? email[0].toUpperCase() : '?';
  }

  function wireHeaderButtons() {
    const minBtn = document.getElementById('btn-minimize');
    const closeBtn = document.getElementById('btn-close');

    if (minBtn) {
      minBtn.addEventListener('click', function () {
        window.pywebview.api.minimize_window();
      });
    }
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        window.pywebview.api.close_window();
      });
    }
  }

  function wireCollapsibles() {
    document.querySelectorAll('.section-header.collapsible').forEach(function (header) {
      header.addEventListener('click', function () {
        const targetId = header.getAttribute('data-target');
        const content = document.getElementById(targetId);
        const indicator = header.querySelector('.collapse-indicator');
        if (!content) return;
        const isCollapsed = content.classList.toggle('collapsed');
        if (indicator) indicator.textContent = isCollapsed ? '▸' : '▾';
      });
    });
  }

  function wireSidebar() {
    const toggle = document.getElementById('sidebar-toggle');
    const app = document.querySelector('.app');
    if (!toggle || !app) return;

    toggle.addEventListener('click', function () {
      const collapsed = app.classList.toggle('sidebar-collapsed');
      toggle.textContent = collapsed ? '▶' : '◀';
      toggle.title = collapsed ? 'Mostrar sidebar' : 'Ocultar sidebar';
    });

    // Botón avatar: muestra info del usuario en un toast
    const avatarBtn = document.getElementById('btn-avatar');
    if (avatarBtn) {
      avatarBtn.addEventListener('click', function () {
        const email = document.getElementById('footer-email')?.textContent || '(sin sesión)';
        const role = document.getElementById('footer-role')?.textContent || '';
        showToast(email + (role ? ' · ' + role : ''));
      });
    }

    // Botón config de la sidebar (mismo comportamiento que el antiguo btn-config)
    const cfgSideBtn = document.getElementById('btn-config-side');
    if (cfgSideBtn) {
      cfgSideBtn.addEventListener('click', function () {
        window.pywebview.api.open_config().then(function (r) {
          showToast((r && r.message) || 'Configuración llega en Fase 5');
        });
      });
    }
  }

  async function init() {
    showState('state-loading');
    wireHeaderButtons();
    wireCollapsibles();
    wireSidebar();

    try {
      const [taskRes, profileRes] = await Promise.all([
        window.pywebview.api.get_active_task(),
        window.pywebview.api.get_current_profile(),
      ]);

      if (profileRes && profileRes.ok) {
        renderProfile(profileRes.profile);
      } else {
        renderProfile(null);
      }

      if (!taskRes || !taskRes.ok) {
        showState('state-error');
        const errMsgEl = document.getElementById('error-detail');
        if (errMsgEl && taskRes && taskRes.error) {
          errMsgEl.textContent = taskRes.error;
        }
        return;
      }
      if (taskRes.task == null) {
        showState('state-empty');
        return;
      }
      renderTask(taskRes.task);
      showState('state-task');
    } catch (e) {
      showState('state-error');
      const errMsgEl = document.getElementById('error-detail');
      if (errMsgEl) errMsgEl.textContent = String(e);
    }
  }

  window.addEventListener('pywebviewready', init);
})();
