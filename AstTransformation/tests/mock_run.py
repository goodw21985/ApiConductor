def fn():
    
    def search_email(a='first', b='second'):
        return {a:{'name':"bob", 'age':10}, b:{'name':'jill', 'age':11}}
    
    def search_dog(a='first', b='second'):
        return a.name+" "+a.age + "," + b.name+" "+b.age
    
    
    a=[search_email('a1','a2'), search_email('a3','a4')]
    return search_dog(a[0]['a1'], a[1]['a4'])
    
print(fn())