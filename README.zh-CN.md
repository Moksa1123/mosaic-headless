# mosaic-headless

直接写入数据模型来构建和修改 [Mosaic Pro](https://mosaicbuilder.com)（Nextend）网站——
不开可视化编辑器，不碰 DOM。

*其他语言：[English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md)*

---

Mosaic 把一个页面放在 **23 张自定义数据表**里，不在 `post_content`，也不在 `postmeta`。
一个元素一行，树状结构靠 `parentID` 字段，同层顺序是一个 fractional-index 字符串。
编辑器只是这个模型的一个客户端。它不是格式本身，你也不需要它。

这个 skill 就是那个模型的地图——**对着真实安装量出来的，不是从源码读出来的**。

## 唯一一条凌驾一切的规则

**绝不凭印象写节点类型、属性名、枚举值、样式键或 Free/Pro 的判断。去 `data/` 里查。**

然后去看页面。Mosaic 有四种失效模式，**其中只有一种会改变 HTTP 状态码**：

```
校验器干净地拒绝      HTTP 200  + body 里一个 exceptions 数组
commit 时 PHP fatal   HTTP 500  （122 种类型里有 15 种，光放在 div 里就会）
结构无效的节点        HTTP 200、已写入、数据库有那一行，然后整个公开页面
                      变成一段 54 字节的错误字符串
值的「形状」错误      HTTP 200、已保存，而那条 CSS 规则就是不存在
该网址没有对应模板    HTTP 406，且对未登录者是空白 body
```

**commit 成功不能当作页面正常的证据。**

## 验证了什么，怎么验的

全部跑在真实安装上——WordPress 7.1、WooCommerce 11.1、Mosaic Pro 1.0.7、**未授权**：
授权管的是主题库和更新，不是节点工厂，所以 Pro 类型照样注册、照样渲染。

| 项目 | 结果 |
|---|---|
| **节点类型** | 122 / 122，一份文档一种类型：写入 → 渲染 → 断言 → 删除。70 RENDERED、30 COMMITTED、15 COMMIT_5xx、7 BROKE_PAGE |
| **样式属性** | 98 / 98 写进真实页面并对照编译后的 CSS：58 COMPILED、18 ABSENT、21 SKIPPED |
| **节点属性** | 181 / 181，用每个属性自己的 validator chain 推导出的值重测：35 APPLIED、42 NO_EFFECT、55 NO_HOST、47 SKIPPED |
| **响应式** | 两个站共 569 条 `_t`/`_m` 声明，对照网站实际送出的样式表逐条断言——全部通过 |
| **主题导出／导入** | 完整往返验证：导出整个主题、以副本身份导入，副本送出的页面逐字节相同 |
| **线上量测** | 114 条 REST 路由、151 个 element class、59 个条件主体、23 张表 / 206 个字段 |

`SKIPPED`、`NO_HOST`、`INCONCLUSIVE` 永远不并入通过率。
**一个把自己的盲点算成成功的扫描工具，正是这个 skill 要反对的东西。**

### 动手之前值得先知道的两个结果

**带有 `group` 的属性，单独设置一律无效。** 两个方向都精确：78 个无 group 的属性得到
58 COMPILED、0 ABSENT；20 个有 group 的全部 0 COMPILED。所以 `borderLeftWidth`、
`outlineColor`、`gridColumnStart` 是**同一条规则的三个实例**，不是三个各自的怪毛病。
要用就用分组形状——`border` 收 `{width, style, color}`——或者退回 `customStyles`。

**断点覆盖只能「改变」属性，永远不能「移除」。** 窄屏的 `customStyles` 如果只是
没写某条边框，宽屏那条边框会活下来，在塌成单列的版面正中间画一条线。
**要把 `border-left:0` 明确写出来。**

## 工具

```bash
wp eval-file tools/bootstrap_probe_theme.php          # 免授权的测试主题
python tools/build_site.py   --config c.json --site sites/moksa.json
python tools/verify_rwd.py   --config c.json --site sites/moksa.json --csv rwd.csv
python tools/copy_styles.py  --config c.json --from a --to-prefix b- --only "&._m"
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "名称" rebind activate
```

`sites/_moksa.py` 是完整示例：一个真实工作室的首页——报头、规格区块、服务、九行作品表格、
流程、技术栈、产品、客户评价、联系——**590 个节点全部通过数据表写入**，
还有一个用具名 view timeline 做的、会跟随滚动的条款索引，完全没有 JavaScript。

## 从哪里开始读

1. `references/data-model.md` —— 页面到底住在哪里。
2. `references/write-protocol.md` —— checkout / check / commit。
3. `references/failure-modes.md` —— Mosaic 怎么坏的，都是量出来的。**动笔前先读。**
4. `references/responsive.md` —— state / breakpoint / property 这个轴。
5. `references/styling.md` —— 一个样式值怎么变成 CSS。
6. `references/design-system.md` —— element class 与设计 token。

## 许可

MIT。Mosaic Pro 本身是有授权的第三方软件，**不包含**在这个 repo 里。
