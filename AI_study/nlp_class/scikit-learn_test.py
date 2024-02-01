from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


# 加载数据集
iris = load_iris()
X = iris.data
y = iris.target

print(f"iris = {iris}")


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
print(f"X_train = {X_train}")
print(f"X_test = {X_test}")
print(f"y_train = {y_train}")
print(f"y_test = {y_test}")


model = RandomForestClassifier(n_estimators=100)


model.fit(X_train, y_train)

predictions = model.predict(X_test)

print(f"X_test = {X_test}")
print(f"predictions = {predictions}")
print("Accuracy:", accuracy_score(y_test, predictions))




