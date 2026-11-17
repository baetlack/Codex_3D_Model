# 总装维护

先读 README.md、assembly.json 与 data/对齐依据.json。总装本地Z0为EL100，东X/北Y/上Z。

只通过总装刚性变换和就位表组合源模型，不改动已确认桥架连接件或设备形状。无依据的标高、管口朝向和设备位置明确列为待核，未定位设备不进入场景和碰撞检查。D41B02B1的约200mm修正仅作用于总装实例，保留原坐标与依据。

修改提取逻辑后运行 tools/project.py build、tools/test_geometry.py 与 tools/project.py check；修改浏览器后重新验证界面，更新 data/浏览器检查.json、预览和 tools/project.py snapshot。碰撞报告区分候选包围盒与实际几何相交。不得把初版相交清单宣称为全部施工冲突，或把源模型的示意尺寸当成确认值。
