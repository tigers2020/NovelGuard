export const SETTINGS_KEY_INCLUDE_RELATION = "include_relation";

export type AppSettingKey =
  | typeof SETTINGS_KEY_INCLUDE_RELATION
  | "scan.extensionFilter"
  | "scan.includeSubdirs"
  | "scan.includeHidden"
  | "scan.incrementalScan"
  | "scan.includeSymlinks";

export type AppSettingValue = string | boolean;

export type AppSettingSource = "default" | "persisted";

export type AppSettingResponse = {
  key: AppSettingKey;
  value: AppSettingValue;
  source: AppSettingSource;
};
