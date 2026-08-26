# Claude Cream 仓库分析与 IDEA 映射

## 分析基线

- 仓库：`kakarrot-dev/claude-cream`
- 提交：`a1e8d64cb4de3a8e0d5e31b695f37239b0f172b0`
- 上游 token 版本：`1.0.0`
- 分析日期：`2026-08-26`

上游不是单一编辑器皮肤，而是一套跨 Codex、VS Code、Zed、Typora、Obsidian、Ghostty、网站和
图像生成使用的视觉语言。它的稳定核心是 `tokens/tokens.json`，现有 VS Code 和 Zed 主题则展示了
这些 token 在编辑器 UI、语法、终端、VCS 和状态提示中的实际语义。

## 视觉语言

1. **暖而不黄。** Light 的基础画布是 `#f5f3e9`，编辑器使用略亮的 `#f8f7f2`，浮层使用纯白，
   通过轻微明度差而非冷灰阴影建立层级。
2. **深而不黑。** Dark 的画布是 `#2d2e2d`，工具栏与标签栏下沉到 `#242524`，弹层提升到
   `#303030` / `#343533`，避免硬黑背景。
3. **琥珀只负责注意力。** Light 使用 `#b7791f`，Dark 使用 `#e6bf7a`；它们用于焦点、按钮、
   光标、活动标签和少量语法标签，不大面积铺底。
4. **状态色保持低饱和。** 青色表示信息与链接，草木绿表示成功与类型，暖红表示错误；都与暖色画布协调。
5. **语法强调编辑结构。** 关键字使用紫色，字符串和类型使用两档绿色，函数和数字使用琥珀/橙色，
   标点保留接近正文的中性色。

## IDEA 层级映射

| IDEA 区域 | Light | Dark | 来源 |
|---|---:|---:|---|
| 应用画布 | `#f5f3e9` | `#2d2e2d` | `colors.*.canvas` |
| 编辑器 | `#f8f7f2` | `#2d2e2d` | `editor.*.canvas-default` |
| 标签栏/状态栏 | `#f0eee6` | `#242524` | `canvas-inset` |
| 输入框/弹层 | `#ffffff` | `#303030` | `canvas-overlay` |
| 边框 | `#d8d2c3` | `#3d3d3a` | `border-default` |
| 主文字 | `#403d36` | `#ddd9cd` | `foreground-default` |
| 焦点/光标 | `#b7791f` | `#e6bf7a` | `focus` |
| 编辑器选区 | `#e6d7b7` | `#695735` | `selection` |
| 当前行 | `#f0eee6` | `#343533` | `line-highlight` |

## 语法映射

| 语义 | Light | Dark | IDEA 属性族 |
|---|---:|---:|---|
| Keyword | `#6f3f82` | `#c891d9` | `DEFAULT_KEYWORD` |
| String | `#536b2c` | `#b5c88d` | `DEFAULT_STRING` |
| Comment | `#756e62` | `#9da39a` | line/block/doc comment |
| Function | `#8a5e16` | `#e5c07b` | function/method call and declaration |
| Type | `#4f6f2b` | `#98c379` | class/type reference |
| Variable | `#2f3440` | `#abb2bf` | identifier/field/parameter |
| Number | `#8a5e16` | `#d19a66` | number/constant |
| Operator | `#4c463b` | `#d6cbc0` | operation sign |
| Punctuation | `#5b554b` | `#b8b2a8` | braces/brackets/delimiters |
| Tag | `#b7791f` | `#e6bf7a` | HTML/XML tags and metadata |
| Attribute | `#4f6f2b` | `#98c379` | HTML/XML attributes |

IDEA 的语言插件通常继承 `DEFAULT_*` 属性，因此 Java、Kotlin、JavaScript、TypeScript、Python、Go、
Rust、SQL 等常见语言会获得一致的语义色。HTML/XML 另有显式覆盖，避免标签和属性回退到平台蓝色。

## 状态与 Diff

- Added / Success：Light `#4b6f3d`，Dark `#9ab889`
- Modified / Warning：Light `#8a5e16`，Dark `#e6bf7a`
- Deleted / Error：Light `#7c1b13`，Dark `#ea928a`
- Renamed / Info：Light `#2c6f75`，Dark `#75b5bc`
- Diff 背景直接使用上游 `diff-added`、`diff-removed`、`diff-modified`

这些色值同时用于错误条、VCS 文件状态、控制台和 Diff，从而减少同一状态在不同工具窗中发生语义漂移。

## 对比度

所有结果均相对于编辑器画布计算：

| 项目 | Light | Dark |
|---|---:|---:|
| 正文 | 10.10:1 | 9.66:1 |
| 注释 | 4.70:1 | 5.28:1 |
| 关键字 | 7.23:1 | 5.52:1 |
| 字符串 | 5.58:1 | 7.54:1 |
| 函数 | 5.30:1 | 7.89:1 |
| 类型 | 5.38:1 | 6.76:1 |

正文与注释均达到 WCAG AA 普通文本 4.5:1 门槛。主题保留上游注释色，没有为了更高对比而引入冷白或冷灰。

## 兼容策略

- `themeProvider` 是 IntelliJ Platform 的资源型扩展点，无需运行时代码。
- Theme JSON 继承平台稳定的 `IntelliJ` / `Darcula` 父主题。
- Editor scheme 使用版本 `142` 和通用 `DEFAULT_*` 属性。
- 插件最低构建号为 `243`，不设置最高构建号。
- UI 覆盖优先选择 2024.3、2025.x 共用的键；新版本未知键由父主题安全回退。

## 有意没有复制的内容

- 没有复制上游字体文件；JetBrains Mono 已随 IDEA 提供，UI 字体继续尊重操作系统与 IDEA 设置。
- 没有加入 VS Code 的 High Contrast 和 Dark Dimmed 变体；本次默认范围为一套 Light/Dark 双主题。
- 没有替换 IDEA 的整套图标；大量重染图标会削弱平台语义并增加跨版本维护成本。
