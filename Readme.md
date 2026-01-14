```python
conda create -n guanhelujue python=3.10
conda activate guanhelujue
pip install -r requirements.txt
```



注意三点
1、basicsr和gfpgan两个库需要使用--no-deps来下载

2、下载facexlib的时候不要下载tb-nightly

3、在cosyvoice的src文件目录下的file_utils的第45行删掉backend参数

4、在sadtalker的src文件目录下的utils文件夹下的croper的第131行由

```python
# 🔴 错误代码
raise 'can not detect the landmark from source image'
```

改为

```python
# 🟢 修正代码
raise Exception('can not detect the landmark from source image')
```
