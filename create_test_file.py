import pandas as pd

# 테스트 데이터 생성
df1 = pd.DataFrame({
    'A': [1, 2, 3, 4, 5],
    'B': ['a', 'b', 'c', 'd', 'e'],
    'C': [100, 200, 300, 400, 500]
})

df2 = pd.DataFrame({
    'X': [10, 20, 30],
    'Y': ['x', 'y', 'z'],
    'Z': [1000, 2000, 3000]
})

# 엑셀 파일로 저장
with pd.ExcelWriter('test_simple.xlsx') as writer:
    df1.to_excel(writer, sheet_name='시트1', index=False)
    df2.to_excel(writer, sheet_name='시트2', index=False)

print('✅ 테스트 파일 생성 완료: test_simple.xlsx')
print(f'시트1: {len(df1)}행 × {len(df1.columns)}열')
print(f'시트2: {len(df2)}행 × {len(df2.columns)}열')
