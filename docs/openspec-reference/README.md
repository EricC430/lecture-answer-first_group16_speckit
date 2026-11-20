# OpenSpec 組規格參考（跨組行為基準）

本目錄收錄同大組 OpenSpec 組的 5 份能力規格，作為兩組系統「功能一致」的行為基準（見憲章原則 I 與 [`docs/alignment.md`](../alignment.md)）。

## 來源與取得日期

- **來源**：OpenSpec 組提供的 `specs/` 目錄（各能力一份 `spec.md`），由 jacky0407 自對方交付的檔案複製。
- **取得日期**：2026-11-20
- **對方 repo／commit**：尚未取得，已列入 `docs/alignment.md` 待確認問題。
- **處理方式**：原封不動複製，未修改任何內容（含標題 `# Spec Delta` 與 `## ADDED Requirements`）。`.gitattributes` 已對本目錄的 `spec.md` 關閉換行轉換，確保與來源逐位元一致。

## 檔案與對應子功能

| OpenSpec 能力 | 檔案 | SpecKit 子功能 | SHA-256 |
|---|---|---|---|
| activity-session | [activity-session/spec.md](activity-session/spec.md) | `001-activity-session` | `fece748f3cf5bad56e0d4c26e7b082cd0796e2804071b62988b9bb4aae4b11ce` |
| guided-notes-import | [guided-notes-import/spec.md](guided-notes-import/spec.md) | `002-guided-notes-import` | `c932f2604e0db24c9f5d5f39a0d839be513f593f6e11adce74dece95553ab798` |
| round-submission | [round-submission/spec.md](round-submission/spec.md) | `003-round-submission` | `1eb2cb07c04a39279f871a1acf7841a307780e6490bde9f71544978a61d33fdc` |
| ranking-review | [ranking-review/spec.md](ranking-review/spec.md) | `004-ranking-review` | `7a243602279aa7f22f33436903cb171df7749d2efe951783ec5c56c4615bd23f` |
| result-export | [result-export/spec.md](result-export/spec.md) | `005-result-export` | `9d7c7710bef32d719a48d530b6e099afc26bab15306a67a4789a53b10bc3f8c7` |

## 使用規則

- **不得直接修改**本目錄的 `spec.md`。對方更新規格時，整份重新複製、更新上表的取得日期與雜湊，並在 `docs/alignment.md` 記錄差異與影響範圍。
- 每份 SpecKit 子功能 spec 必須標註其對應的 OpenSpec Requirement 名稱（例如「活動建立與老師權限」）。
- 任何偏離或新增行為，先記入 `docs/alignment.md` 並經雙方確認後才能實作。
- 驗證雜湊：`sha256sum docs/openspec-reference/*/spec.md`
