import os
import requests

code = """import pandas as pd
import matplotlib.pyplot as plt


# 创建数据框
data = {
    '序号': [1, 2, 3, 4, 5, 6],
    '工作部门': ['学生工作部', '学生工作部', '艺术设计学院', '艺术设计学院', '艺术设计学院', '教师发展中心'],
    '岗位代码': ['FDY1', 'FDY2', 'JS1', 'JS2', 'JS3', 'XZ1'],
    '招聘对象': ['应届毕业生', '不限', '不限', '不限', '不限', '不限'],
    '招聘岗位': ['辅导员', '辅导员', '数字媒体艺术设计专任教师', '视觉传达设计专任教师', '非遗学院专任教师', '科员'],
    '岗位等级': ['专业技术岗位十一级', '专业技术岗位十一级', '专业技术岗位十一级', '专业技术岗位十一级', '专业技术岗位十一级', '管理岗位九级'],
    '人数': [4, 3, 1, 1, 1, 1],
    '学历学位': ['硕士研究生及以上', '硕士研究生及以上', '硕士研究生及以上', '硕士研究生及以上', '硕士研究生及以上', '硕士研究生及以上']
}

df = pd.DataFrame(data)

# 创建图表
plt.figure(figsize=(15, 10))

# 部门招聘人数柱状图
plt.subplot(2, 2, 1)
dept_counts = df.groupby('工作部门')['人数'].sum()
dept_counts.plot(kind='bar', color=['skyblue', 'lightgreen', 'salmon'])
plt.title('各部门招聘人数')
plt.ylabel('人数')
plt.xticks(rotation=0)

# 岗位类型分布饼图
plt.subplot(2, 2, 2)
job_counts = df.groupby('招聘岗位')['人数'].sum()
job_counts.plot(kind='pie', autopct='%1.1f%%', colors=['gold', 'lightcoral', 'lightskyblue', 'lightgreen'])
plt.title('岗位类型分布')
plt.ylabel('')

# 学历要求饼图
plt.subplot(2, 2, 3)
degree_counts = df.groupby('学历学位')['人数'].sum()
degree_counts.plot(kind='pie', autopct='%1.1f%%', colors=['lightblue'])
plt.title('学历要求分布')
plt.ylabel('')

# 招聘对象分布饼图
plt.subplot(2, 2, 4)
target_counts = df.groupby('招聘对象')['人数'].sum()
target_counts.plot(kind='pie', autopct='%1.1f%%', colors=['lightgreen', 'orange'])
plt.title('招聘对象分布')
plt.ylabel('')

plt.tight_layout()
plt.savefig('招聘岗位数据报表.png')
plt.show()"""   


payload = {"code": code}
url = "http://127.0.0.1:16010/ai/sandbox/v1/api/execute_sync"

response = requests.post(url, json=payload)

print(response.status_code)
print(response.text)

# 保存返回的图片
if response.status_code == 200:
    import base64
    
    result = response.json()
    if result.get('resultCode') == 0 and 'data' in result and 'images' in result['data']:
        images = result['data']['images']
        if images:
            # 解码第一张图片并保存
            image_data = base64.b64decode(images[0])
            save_dir = "tmp"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            with open(os.path.join(save_dir, 'generated_chart.png'), 'wb') as f:
                f.write(image_data)
            print(f"图片已保存为 {os.path.join(save_dir, 'generated_chart.png')}")
        else:
            print("没有找到图片数据")
    else:
        print("API调用失败或返回格式异常")
else:
    print(f"HTTP请求失败，状态码: {response.status_code}")
