export type ResolveAutoApproveSummary = {
  unreviewedCount: number;
  keeperCount: number;
  moveCandidateCount: number;
  exactCount: number;
  nearCount: number;
  relationCount: number;
  skippedConflictCount: number;
  skippedExcludedCount: number;
  keeperRowIds: string[];
  samples: {
    keepers: string[];
    moveCandidates: string[];
    exact: string[];
    near: string[];
    relation: string[];
  };
};
