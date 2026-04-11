# protocols

에이전트·기여자가 따르는 **절차 요약**이다. 세부 톤·역할 대사는 `.cursor/rules/persona-dialogue.mdc` 와 [persona/README.md](../persona/README.md)를 본다.

## 기획과 코딩의 분리 ([AGENTS.md](../AGENTS.md))

1. **리서치**: 관련 코드·규칙을 읽고 조사 메모를 [documents/](../documents/)에 남긴다.  
2. **플랜**: 변경 범위·경로·트레이드오프를 담은 플랜 MD를 **같은 `documents/`** (또는 팀이 정한 하위 폴더)에 둔다.  
3. **승인**: 사람이 플랜 본문을 검토·수정·승인한다.  
4. **구현**: 승인 후에만 코드를 수정한다.

플랜이 닫히기 전에는 Persona Dialogue 3단계의 "구현 진입"을 허용하지 않는다.

## Cursor 규칙 우선순위

1. `.cursor/rules/root.mdc`  
2. `architecture.mdc`  
3. 그 외 glob 규칙
