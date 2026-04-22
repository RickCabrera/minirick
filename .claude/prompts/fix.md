Bug fix menor en src/minirick/launcher.py, función _launch_vscode:

En Windows, `code` es un wrapper .cmd (verificamos con shutil.which → devuelve code.CMD). subprocess.Popen con shell=False falla con WinError 2 al intentar ejecutar un .cmd. Fix: usar shell=True en Windows.

Cambio exacto en _launch_vscode, después de calcular `path`:

  if IS_WINDOWS:
      subprocess.Popen(f'code "{path}"', shell=True)
  else:
      subprocess.Popen(["code", path], shell=False)
  return f"VSCode abierto en {path}"

Añade test en tests/test_launcher.py:

def test_vscode_uses_shell_on_windows(monkeypatch):
    monkeypatch.setattr(launcher, "IS_MAC", False)
    monkeypatch.setattr(launcher, "IS_WINDOWS", True)
    monkeypatch.setattr(launcher.shutil, "which", lambda name: r"C:\fake\code.CMD")
    popen_mock = MagicMock()
    monkeypatch.setattr(launcher.subprocess, "Popen", popen_mock)
    result = launcher.launch_tool(Tool(type="vscode", path="C:/x"))
    assert result["ok"] is True
    args, kwargs = popen_mock.call_args
    assert kwargs.get("shell") is True
    assert isinstance(args[0], str)
    assert "code" in args[0]

Actualiza el test existente test_vscode_launches si aserta shell=False — ahora depende del SO. Agrega un test paralelo test_vscode_uses_list_on_mac con IS_MAC=True que verifique shell=False y args[0] es una lista.

pytest debe terminar con 58 tests (57 previos + 2 nuevos = 59, o 58 si reemplazas uno existente). NO commit.