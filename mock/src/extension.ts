import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  let disposable = vscode.commands.registerCommand('mock.start', async () => {
    const input = await vscode.window.showInputBox({ prompt: 'Ask something to Mock' });
    if (input) {
      vscode.window.showInformationMessage(`You asked: "${input}" — and Mock replied: "42"`);
    }
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {}
