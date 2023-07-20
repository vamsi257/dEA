import pandas as pd
import ast
import json

print("Press 1 CSV to Transpose")
print("Press 2 json to Transpose")
option=int(input("Enter a option number:"))

if option==1:
    filename=input("please Enter a csv file path with name:")
    df=pd.read_csv(filename)
elif option==2:
    filename=input("please Enter a json file path with name:")
    with open(filename,'r') as f:
        data = json.load(f)
    res=ast.literal_eval(data)
    df=pd.DataFrame(columns=['folder_name','filename','Page_n','id','field_name','label_data'])
    for i in range(0,len(res)):
        df.loc[i]=[res[i]['folder_name'],res[i]['filename'],res[i]['Page_n'],res[i]['id'],res[i]['field_name'],res[i]['label_data']]
    


allvalue=[]
s=df['label_data']
for i in s:
    allvalue.append(i)
    
allcolums=df['field_name']
colums=[]
c=0
for i in allcolums:
    if i not in colums:
        p=allvalue[c].replace('\n'," ")
        df[i]=p
        c+=1
    else:
        c+=1
if option==2:
    newdf=df.drop(['id', 'field_name', 'label_data'],axis=1)
elif option==1:
    newdf=df.drop(['id', 'field_name', 'label_data',r'format\n'],axis=1)
    
df1 = newdf.drop_duplicates(keep='first')

download=input("Enter a download path with file name and with extention(.csv):")
df1.to_csv (download, index = None, header=True) 
    
    

