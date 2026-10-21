# Spotlight 支持说明（本 fork 的改动）

这是 [TomBadash/Mouser](https://github.com/TomBadash/Mouser) 的一个 fork，给这个
"Options+ 替代品" 加了一层**屏幕聚光灯**能力，让演示时不需要装 Logi Options+ 也能
"指哪亮哪"。

上游 Mouser 的定位是 HID++ 鼠标的按键/手势重映射，本身不具备任何屏幕绘制能力，
也没有演示器（presenter）概念。这里新增的是独立的一层，不改变原有鼠标逻辑。

---

## 1. 加了什么

| 改动 | 文件 |
|---|---|
| 全屏聚光灯/激光点覆盖层（点击穿透、置顶、跟随光标、多屏） | `ui/spotlight_overlay.py`（新增） |
| 两个新动作 `spotlight_hold` / `spotlight_toggle` | `core/key_simulator.py` |
| 按下/抬起分别点亮与熄灭的路由 | `core/engine.py` |
| QML 后端属性、槽、预览 | `ui/backend.py` |
| "聚光灯" 设置页 | `ui/qml/SpotlightPage.qml`（新增）、`ui/qml/Main.qml` |
| 导航图标 | `images/icons/spotlight.svg`（新增） |
| 中英文文案 | `ui/locale_manager.py` |
| 配置默认值 `spotlight_*` | `core/config.py` |
| 测试 | `tests/test_spotlight.py`、`tests/test_spotlight_overlay.py` |

功能上等价于 Logi Options+ 里的 Highlight（聚光斑）与 Laser（激光点），
没有做 Magnify（放大镜）和演示计时器。

## 2. 怎么跑起来

```bash
git clone <this-fork> Mouser
cd Mouser
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main_qml.py
```

打包：`build.bat`（Windows）/ `Mouser.spec`，与上游一致。

## 3. 怎么用

1. 打开 Mouser → **鼠标与配置文件** 页
2. 点任意一个按键（侧键、中键、手势键都行）→ 动作列表里选
   **Presentation → Spotlight (hold to highlight)**
3. 演示时**按住**这个键：整屏压暗，光标处亮起一个圆；松手恢复
4. 想要"按一下开、再按一下关"，就选 **Spotlight (toggle highlight)**
5. 在侧边栏 **聚光灯** 页调样式：聚光斑/激光点、光斑大小、背景压暗、圆环粗细、颜色，
   并有 2.5 秒的预览按钮

配合罗技 Spotlight 演示器（免驱模式）：按住遥控器的"指针键"时，遥控器本身就在
移动系统光标，所以只要把这个键映射到 `spotlight_hold`，按住即出光斑、移动手即跟随。
如果遥控器的指针键在 HID++ 层不可重映射，退一步用 `toggle` 版本绑在侧键上也能用。

## 4. 实现取向：为什么不直接读遥控器的运动数据

Spotlight 的"原生"效果是客户端渲染：Options+ 读取设备的运动数据（HID++
`0x1A01 sensor3D`），自己算坐标、隐藏系统光标、画光斑。要做到那一步，需要：

1. 识别演示器（USB `0xC53E`、蓝牙 `0xB503`，Spotlight 2 为 `0xC548` / `0xB506`）
2. 抓 `0x1A00 presenterControl` 的按键通知与运动报告
3. 自己做指针积分、坐标映射、隐藏光标

现成参考实现：[Projecteur](https://github.com/jahnf/Projecteur)（C++/Qt，Linux）、
[spotlight.js](https://github.com/manekinekko/spotlight.js)（WebHID）。Mouser 的
`core/hid_gesture.py` 已经有完整的 HID++ 栈（`_request` / `_find_feature` /
`_on_report` / `_tx` / `_rx`），再写一个 presenter 模块是可行的下一步。

这一版选择**复用系统光标**这条路：零逆向、任何指点设备都能用、Windows/macOS/Linux
行为一致。代价是光斑位置 = 系统光标位置，指针加速度由系统决定，且不隐藏系统光标。

## 5. 已知限制

- **不能盖住独占全屏**：覆盖层是 `Qt.Tool` + `FramelessWindowHint` 的无边框窗口，
  PowerPoint / Keynote 的放映窗口（无边框普通窗口）没问题，DirectX 独占全屏盖不住。
- **不隐藏系统光标**：Options+ 会把系统光标藏起来只留光斑；这里两者同时可见。
  激光点模式下建议自己在系统里关掉指针，或在 PowerPoint 里用 Ctrl+L 切激光笔。
- **多显示器**：覆盖层跟着光标跳到当前屏幕，只遮当前屏；不做跨屏连续遮罩。
- **高 DPI**：用 Qt 的设备无关坐标，缩放 125%/150% 下半径按逻辑像素算。
- **性能**：光标不动时不重绘；4K 全屏每帧填充一次，30–60 fps 量级，独显/核显都够。

## 6. 配置键（`config.json` → `settings`）

| 键 | 默认 | 说明 |
|---|---|---|
| `spotlight_radius` | `220` | 光斑半径（逻辑像素，20–1200） |
| `spotlight_dim` | `0.55` | 背景压暗程度（0–0.95） |
| `spotlight_mode` | `"spotlight"` | `"spotlight"` 或 `"laser"` |
| `spotlight_color` | `"#00d4aa"` | 圆环/激光点颜色 |
| `spotlight_ring_width` | `3` | 圆环粗细（0 表示不画环） |

UI 里的改动会即时写回配置。

## 7. 测试

```bash
# 不依赖 Qt：动作注册、按下/抬起路由、映射注册
python -m unittest tests.test_spotlight -v

# 需要 PySide6：覆盖层的显示/隐藏/绘制/多屏（无 Qt 时自动 skip）
QT_QPA_PLATFORM=offscreen python -m unittest tests.test_spotlight_overlay -v
```

## 8. 后续 TODO

- [ ] 演示器设备识别（按 VID/PID 与接收器槽位），在设备卡片里显示"Spotlight"
- [ ] HID++ `0x1A00` / `0x1A01` 直读运动数据，自己画指针（不依赖系统光标）
- [ ] 放大镜模式（抓屏 + 放大）
- [ ] 演示计时器（到点震动，复用 haptic 通道）
- [ ] 光斑形状选择（圆形/椭圆/矩形）与动画淡入淡出
