/* minirick dashboard — frontend logic (vanilla, no framework) */

(function () {
  'use strict';

  const STATE_IDS = ['state-loading', 'state-error', 'state-empty', 'state-task'];

  // Último estado visible antes de abrir el panel admin, para poder volver.
  let _lastVisibleStateId = 'state-task';
  let _currentRole = null;
  let _profilesCache = [];
  let _tasksCache = [];

  function showState(stateId) {
    for (const id of STATE_IDS) {
      const el = document.getElementById(id);
      if (el) el.hidden = id !== stateId;
    }
    _lastVisibleStateId = stateId;
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
      _currentRole = null;
      applyRoleVisibility();
      return;
    }

    const email = profile.email || '';
    const role = profile.role || '';

    if (emailEl) emailEl.textContent = email;
    if (roleEl) roleEl.textContent = role;
    if (avatarEl) avatarEl.textContent = email.length > 0 ? email[0].toUpperCase() : '?';

    _currentRole = role;
    applyRoleVisibility();
  }

  function applyRoleVisibility() {
    // Solo admin/owner ven el botón de config que abre el panel admin.
    const btn = document.getElementById('btn-config-side');
    if (!btn) return;
    const isAdmin = _currentRole === 'admin' || _currentRole === 'owner';
    btn.hidden = !isAdmin;
  }

  // ---------- Admin panel ----------

  function openAdminPanel() {
    const panel = document.getElementById('admin-panel');
    if (!panel) return;
    // Ocultar cualquier state-* activo.
    STATE_IDS.forEach(function (id) {
      const el = document.getElementById(id);
      if (el && !el.hidden) {
        _lastVisibleStateId = id;
        el.hidden = true;
      }
    });
    panel.hidden = false;

    const profilesEl = document.getElementById('admin-profiles');
    const tasksEl = document.getElementById('admin-tasks');
    if (profilesEl) profilesEl.innerHTML = '<div class="empty-inline">cargando...</div>';
    if (tasksEl) tasksEl.innerHTML = '<div class="empty-inline">cargando...</div>';

    Promise.all([
      window.pywebview.api.list_profiles(),
      window.pywebview.api.list_all_tasks(),
    ])
      .then(function (results) {
        const profRes = results[0];
        const taskRes = results[1];

        if (!profRes || !profRes.ok) {
          _profilesCache = [];
          if (profilesEl) {
            profilesEl.innerHTML =
              '<div class="empty-inline">No tienes permiso o no hay perfiles.</div>';
          }
        } else {
          _profilesCache = profRes.data || [];
          renderAdminProfiles(_profilesCache);
        }

        if (!taskRes || !taskRes.ok) {
          _tasksCache = [];
          if (tasksEl) {
            tasksEl.innerHTML =
              '<div class="empty-inline">No se pudieron leer las tareas: ' +
              escapeHtml((taskRes && taskRes.error) || '') +
              '</div>';
          }
        } else {
          _tasksCache = taskRes.data || [];
          renderAdminTasks(_tasksCache, _profilesCache);
        }
      })
      .catch(function (e) {
        showToast('Error: ' + e);
      });
  }

  function closeAdminPanel() {
    const panel = document.getElementById('admin-panel');
    if (panel) panel.hidden = true;
    const target = _lastVisibleStateId || 'state-task';
    const el = document.getElementById(target);
    if (el) el.hidden = false;
  }

  function renderAdminProfiles(profiles) {
    const el = document.getElementById('admin-profiles');
    if (!el) return;
    if (!profiles || profiles.length === 0) {
      el.innerHTML = '<div class="empty-inline">Sin perfiles.</div>';
      return;
    }
    el.innerHTML = profiles
      .map(function (p) {
        return (
          '<div class="admin-profile-row">' +
          '<span class="admin-profile-email">' +
          escapeHtml(p.email || '') +
          '</span>' +
          '<span class="admin-profile-role">' +
          escapeHtml(p.role || '') +
          '</span>' +
          '</div>'
        );
      })
      .join('');
  }

  function renderAdminTasks(tasks, profiles) {
    const el = document.getElementById('admin-tasks');
    if (!el) return;
    if (!tasks || tasks.length === 0) {
      el.innerHTML = '<div class="empty-inline">Sin tareas.</div>';
      return;
    }
    const emailsById = {};
    (profiles || []).forEach(function (p) {
      emailsById[p.id] = p.email;
    });
    el.innerHTML = tasks
      .map(function (task) {
        const assigneeIds = task.assignees || [];
        const assigneeSet = {};
        assigneeIds.forEach(function (id) {
          assigneeSet[id] = true;
        });

        const checkboxesHtml = (profiles || [])
          .map(function (p) {
            const checked = assigneeSet[p.id] ? 'checked' : '';
            return (
              '<label class="assignee-checkbox">' +
              '<input type="checkbox" data-email="' +
              escapeHtml(p.email || '') +
              '" ' +
              checked +
              ' /> ' +
              escapeHtml(p.email || '') +
              '</label>'
            );
          })
          .join('');

        const activeMark = task.is_active ? '[active]' : '[activar]';
        return (
          '<div class="admin-task-row" data-task-id="' +
          escapeHtml(task.id) +
          '">' +
          '<div class="admin-task-head">' +
          '<span class="admin-task-title">' +
          escapeHtml(task.title || '(sin título)') +
          '</span>' +
          renderStatusBadge(task.status) +
          '<button class="admin-activate-btn" data-task-id="' +
          escapeHtml(task.id) +
          '">' +
          activeMark +
          '</button>' +
          '</div>' +
          '<div class="admin-task-assignees">' +
          (checkboxesHtml || '<span class="empty-inline">(sin colabs)</span>') +
          '</div>' +
          '</div>'
        );
      })
      .join('');

    el.querySelectorAll('.admin-activate-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const tid = btn.getAttribute('data-task-id');
        const row = el.querySelector(
          '.admin-task-row[data-task-id="' + tid.replace(/"/g, '') + '"]'
        );
        const checked = [];
        if (row) {
          row
            .querySelectorAll('input[type="checkbox"]')
            .forEach(function (cb) {
              if (cb.checked) checked.push(cb.getAttribute('data-email'));
            });
        }
        window.pywebview.api
          .set_task_active(tid, checked)
          .then(function (r) {
            if (!r || !r.ok) {
              showToast('Error: ' + ((r && r.error) || 'desconocido'));
            } else {
              showToast('Tarea activada');
              openAdminPanel(); // refresca la vista
            }
          })
          .catch(function (e) {
            showToast('Error: ' + e);
          });
      });
    });
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

    // Botón config de la sidebar → abre/cierra el panel admin (solo admin/owner lo ve).
    const cfgSideBtn = document.getElementById('btn-config-side');
    if (cfgSideBtn) {
      cfgSideBtn.addEventListener('click', function () {
        const panel = document.getElementById('admin-panel');
        if (panel && !panel.hidden) {
          closeAdminPanel();
        } else {
          openAdminPanel();
        }
      });
    }

    // Botón cerrar del panel admin.
    const adminCloseBtn = document.getElementById('btn-admin-close');
    if (adminCloseBtn) {
      adminCloseBtn.addEventListener('click', closeAdminPanel);
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
