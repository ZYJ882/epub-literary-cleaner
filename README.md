# EPUB Literary Cleaner

用于整理、修复、审查中文文学类 EPUB，并依据最终 EPUB 提取干净 UTF-8 TXT 的 Manus Skill。

## 项目用途

这个 Skill 面向中文小说、文学合订本和长篇 EPUB 的整理工作。它把“结构审查”和“正文清理”分开处理：先根据 EPUB 的 `OPF`、`spine`、`NCX/nav` 检查卷章顺序，再根据证据处理乱码目录、制作错误造成的重复、缺失章节和章节衔接异常。

适合以下任务：

- 保留原版封面、插图、CSS、字体、元数据和分级目录的 EPUB 修复；
- 检查章节缺失、章节重复、卷章错位和前后文不连贯；
- 区分作者有意的回忆、回环、照应与 EPUB 转换错误；
- 根据最终 EPUB 输出去除图片页、HTML/XML、网页残留的干净 TXT；
- 保留卷—章节树状结构和合法的序章、楔子、终章、尾声、读者信等正文单元。

本仓库只包含 Skill、脚本和文档，不包含任何用户上传的 EPUB、TXT 正文或图片。

## 作为 Manus Skill 使用

下载或安装本仓库后，把 `SKILL.md` 和 `scripts/` 放在同一个 Skill 目录中。然后可以直接提出：

- “整理并修复这个 EPUB，输出 EPUB 和 TXT”；
- “检查章节是否缺失、重复或前后文接不上”；
- “根据这个 EPUB 生成干净 TXT，保留分卷结构”；
- “保留原版图片和目录，只修正文中的制作错误”。

核心原则写在 [`SKILL.md`](SKILL.md) 中。

## 直接生成干净 TXT

脚本以 EPUB 为唯一来源，按 EPUB 原始 NCX/nav 层级提取正文，不按乱码文件名或文件系统顺序排序：

```bash
python3 scripts/epub_to_clean_txt.py input.epub output.txt
```

默认跳过封面、制作说明、内容介绍、角色图鉴和图片页。如果确实需要保留这些前置文字：

```bash
python3 scripts/epub_to_clean_txt.py \
  input.epub output.txt --include-frontmatter
```

脚本会输出卷名、章节标题和正文，保留 NCX/nav 中的卷—章节层级，去除 HTML/XML 标签、图片占位符和 XHTML 转换造成的章节标题重复，并保留末尾《致各位亲爱的读者》等合法顶级正文。

## 审查 EPUB

```bash
python3 scripts/audit_epub.py input.epub
```

审查时应先看报告，再决定是否修改。脚本和 Skill 不会仅凭相似度自动删除疑似作者重复；回环叙事、倒叙、时间冻结和首尾照应必须结合上下文或可靠公开版本判断。

## 目录结构

```text
SKILL.md                         # Manus Skill 主说明
scripts/audit_epub.py            # EPUB 结构与重复审查
scripts/epub_to_clean_txt.py     # 按 EPUB 目录提取干净 TXT
LICENSE                          # MIT License
```

## 验证

```bash
python3 -m py_compile scripts/*.py
python3 scripts/epub_to_clean_txt.py book.epub clean.txt
```

## 重要限制

TXT 没有 EPUB 的 NCX/nav、父子目录和跳转链接，因此 TXT 中的分卷只能以文字标题保留，能否被具体阅读器识别取决于阅读器自身。需要可展开、可点击的分级目录时，应使用 EPUB。

## 许可证

本项目采用 MIT License。使用本 Skill 整理电子书时，请确保拥有相应文件的合法使用权，并遵守适用的版权和平台规则。

## 版本与发布

详细版本变化、升级说明和兼容性信息放在 GitHub [Releases](https://github.com/ZYJ882/epub-literary-cleaner/releases) 中；README 只保留项目用途和使用方法，避免与 Release 历史重复。
