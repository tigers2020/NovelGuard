export type AppBuildType = "dev" | "production" | "packaged";

export interface AppInfo {
  appName: string;
  version: string;
  buildType: AppBuildType;
  gitCommit: string | null;
  builtAt: string | null;
  frontendBuild: string;
  pythonRuntime: string;
}
