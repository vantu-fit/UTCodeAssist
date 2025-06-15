import { machineIdSync } from "node-machine-id";
import * as vscode from "vscode";
import * as URI from "uri-js";

export function translate(range: vscode.Range, lines: number): vscode.Range {
  return new vscode.Range(
    range.start.line + lines,
    range.start.character,
    range.end.line + lines,
    range.end.character,
  );
}

export function getNonce() {
  let text = "";
  const possible =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

export function getExtensionUri(context?: vscode.ExtensionContext): vscode.Uri {
  if (context) {
    return context.extensionUri;
  }
  // Try to find the extension by id (fallback)
  const ext = vscode.extensions.getExtension("utcodeassist.continue");
  if (ext) {
    return ext.extensionUri;
  }
  // Fallback to previous id for compatibility
  const oldExt = vscode.extensions.getExtension("Continue.continue");
  if (oldExt) {
    return oldExt.extensionUri;
  }
  console.warn("Could not find extensionUri. Please provide context to getExtensionUri.");
  throw new Error("Extension URI not found");
}

export function getViewColumnOfFile(
  uri: vscode.Uri,
): vscode.ViewColumn | undefined {
  for (const tabGroup of vscode.window.tabGroups.all) {
    for (const tab of tabGroup.tabs) {
      if (
        (tab?.input as any)?.uri &&
        URI.equal((tab.input as any).uri, uri.toString())
      ) {
        return tabGroup.viewColumn;
      }
    }
  }
  return undefined;
}

export function getRightViewColumn(): vscode.ViewColumn {
  // When you want to place in the rightmost panel if there is already more than one, otherwise use Beside
  let column = vscode.ViewColumn.Beside;
  const columnOrdering = [
    vscode.ViewColumn.One,
    vscode.ViewColumn.Beside,
    vscode.ViewColumn.Two,
    vscode.ViewColumn.Three,
    vscode.ViewColumn.Four,
    vscode.ViewColumn.Five,
    vscode.ViewColumn.Six,
    vscode.ViewColumn.Seven,
    vscode.ViewColumn.Eight,
    vscode.ViewColumn.Nine,
  ];
  for (const tabGroup of vscode.window.tabGroups.all) {
    if (
      columnOrdering.indexOf(tabGroup.viewColumn) >
      columnOrdering.indexOf(column)
    ) {
      column = tabGroup.viewColumn;
    }
  }
  return column;
}

let showTextDocumentInProcess = false;

export function openEditorAndRevealRange(
  uri: vscode.Uri,
  range?: vscode.Range,
  viewColumn?: vscode.ViewColumn,
  preview?: boolean,
): Promise<vscode.TextEditor> {
  return new Promise((resolve, _) => {
    vscode.workspace.openTextDocument(uri).then(async (doc) => {
      try {
        // An error is thrown mysteriously if you open two documents in parallel, hence this
        while (showTextDocumentInProcess) {
          await new Promise((resolve) => {
            setInterval(() => {
              resolve(null);
            }, 200);
          });
        }
        showTextDocumentInProcess = true;
        vscode.window
          .showTextDocument(doc, {
            viewColumn: getViewColumnOfFile(uri) || viewColumn,
            preview,
          })
          .then((editor) => {
            if (range) {
              editor.revealRange(range);
            }
            resolve(editor);
            showTextDocumentInProcess = false;
          });
      } catch (err) {
        console.log(err);
      }
    });
  });
}

export function getUniqueId() {
  const id = vscode.env.machineId;
  if (id === "someValue.machineId") {
    return machineIdSync();
  }
  return vscode.env.machineId;
}
