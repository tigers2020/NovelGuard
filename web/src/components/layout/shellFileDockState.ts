export type ShellFileDockUiState = "empty" | "collapsed" | "expanded";

export function deriveShellFileDockState(args: {
  fileCount: number;
  expanded: boolean;
}): ShellFileDockUiState {
  if (args.fileCount <= 0) {
    return "empty";
  }
  return args.expanded ? "expanded" : "collapsed";
}
