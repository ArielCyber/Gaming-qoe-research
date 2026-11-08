import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import numpy as np
import seaborn as sns

def plot_confusion_matrix(y_test, y_pred):
    cm = confusion_matrix(y_test, y_pred)
    true_labels = ['Bad', 'Poor', 'Fair', 'Good', 'Excellent']
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=true_labels,
                yticklabels=true_labels)
    plt.title('Confusion Matrix')
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.show()

    for i, data in enumerate(cm):
        plt.bar(range(len(data)), data)

        # Set labels and title
        plt.xlabel('Category')
        plt.xticks(range(len(true_labels)), true_labels)
        plt.ylabel('Frequency')
        plt.title(f'True Label {true_labels[i]} Predications')

        # Show the plot
        plt.show()