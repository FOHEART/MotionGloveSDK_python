# tests — MotionGloveSDK Python 单元测试

TDD（测试驱动开发）测试集，方法论与命名规范遵循
`D:\autotools\skills\TDD与GoogleTest实践指南.md`（红/绿/重构循环、
Arrange-Act-Assert 三段式、四类覆盖：金标准 / 不变量 / 边界值 / 异常输入）。

## 运行

```bash
# 项目根目录下
.venv/Scripts/python.exe -m pytest tests/unit -q        # Windows
python3 -m pytest tests/unit -q                         # Linux
```

配置见根目录 `pytest.ini`（testpaths=tests，pythonpath=.）。

## 约束

- 纯 Python，不依赖原生库（MotionGloveSDK.dll/.so）、PySide6、bpy；
  涉及后端的路径用 monkeypatch 哨兵验证「不触碰后端」。
- 测试名格式：`test_被测单元_行为_条件`；docstring 使用五字段模板
  （@test / @brief / @details·目的 / @expected / @priority）。
- 金标准数据必须来自独立推导（半角公式、C++ 源码约定、布局基准），
  不得直接抄实现输出。

## 文件一览

| 文件 | 被测模块 | 覆盖要点 |
| --- | --- | --- |
| test_xsqeconverter.py | xsqeconverter | 半角公式金标准、6 旋转顺序往返不变量、万向锁、非法 order |
| test_decode_glove_csv.py | decode_glove_csv | EULER/QUAT(wxyz) 解析、32 骨映射、异常输入返回 None |
| test_csv_frame_reader.py | csv_frame_reader | 格式 A/B、BOM 兼容、next_frame 末尾契约、seek 夹紧 |
| test_glove_frame_assembler.py | glove_frame_assembler | 分包乱序/重复拼接（无分隔符）、新 fn 重置、异常包 False |
| test_definitions.py | definitions | 骨骼表长度/唯一性、32→42 映射、枚举覆盖 |
| test_abi.py | native/abi | sizeof/offset 布局基准（131/196/8375/6415/10335）、verify_layout |
| test_mapper.py | native/mapper | decode_name、ntohs(5001)、xyzw→wxyz 重排、越界枚举回退、帧头哨兵 |
| test_config_io.py | config_io | 读写 roundtrip、中文非转义、无 .tmp 残留、损坏 JSON 容错 |
| test_motionGloveSDK_api.py | motionGloveSDK | actorName 字节上限 63、无效名称短路不触碰后端 |

## 文档

Doxygen 文档（含本测试集的 @test 文档）由根目录 `Doxyfile` 生成：

```bash
D:/autotools/doxygen-1.11.0/doxygen.exe Doxyfile
# 验收：doxygen_warnings.log 为 0 字节、退出码 0、docs/html/index.html 生成
```
