document.addEventListener("DOMContentLoaded", function() {
    // 固定サイドバーレイアウトのため、開閉用のスクリプトは不要になります。
});

document.addEventListener('DOMContentLoaded', function () {
    // すべての「・・・」ボタンに対してイベントリスナーを設定
    document.querySelectorAll('.action-btn').forEach(button => {
        button.addEventListener('click', function (event) {
            // 親要素の a タグへのクリックイベント伝播を止め、ページ遷移を防ぐ
            event.preventDefault();
            event.stopPropagation();

            // クリックされたボタンの隣にあるメニュー要素を取得
            const menu = this.nextElementSibling;
            
            // 現在表示されている他のメニューをすべて閉じる
            // これにより、複数のメニューが同時に開くのを防ぐ
            document.querySelectorAll('.action-menu.show').forEach(openMenu => {
                if (openMenu !== menu) {
                    openMenu.classList.remove('show');
                }
            });

            // クリックされたボタンに対応するメニューの表示/非表示を切り替える
            menu.classList.toggle('show');
        });
    });

    // ページ上のどこかをクリックしたときに、開いているメニューを閉じる
    document.addEventListener('click', function (event) {
        // クリックされた要素がアクションメニューの領域内でなければ
        if (!event.target.closest('.col-actions')) {
            // 表示されているすべてのメニューを閉じる
            document.querySelectorAll('.action-menu.show').forEach(openMenu => {
                openMenu.classList.remove('show');
            });
        }
    });
});
function renderTaskDetail(task) {
    // 描画先のコンテナ要素を取得
    const container = document.getElementById('task-detail-container');
    if (!container) {
        console.error('描画先のコンテナが見つかりません。');
        return;
    }

    // --- HTML要素を動的に作成 ---

    // 1. 全体を囲む<section>要素
    const section = document.createElement('section');
    section.className = 'task-detail-section';

    // 2. タスクタイトル<h1>要素
    const title = document.createElement('h1');
    title.className = 'task-title';
    title.textContent = task.title;
    
    // ページ全体のタイトルも更新 (Django側で設定済みだが念のため)
    document.title = `${task.title} - タスク詳細`;

    // 3. 詳細項目を作成するヘルパー関数
    const createDetailItem = (label, value) => {
        const div = document.createElement('div');
        div.className = 'detail-item';
        
        const strong = document.createElement('strong');
        strong.textContent = `${label}：`;
        
        const text = document.createTextNode(value);
        
        div.appendChild(strong);
        div.appendChild(text);
        return div;
    };
    
    // Djangoの辞書のキーに合わせてプロパティ名を使用
    const dueDateItem = createDetailItem('期限', task.due_date);
    const assigneeItem = createDetailItem('担当者', task.assignee);
    const descriptionItem = createDetailItem('詳細', task.description);
    const manualItem = createDetailItem('マニュアル', task.manual);

    // 4. ボタンコンテナと各ボタン要素
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'button-container';

    // DjangoのURL構造に合わせてリンクを生成
    const backButton = document.createElement('a');
    backButton.href = '/my-tasks'; // MYタスク一覧へのURL
    backButton.className = 'btn btn-back';
    backButton.textContent = '戻る';

    const returnButton = document.createElement('button');
    returnButton.type = 'button';
    returnButton.className = 'btn btn-return';
    returnButton.textContent = '返却';
    
    const transferButton = document.createElement('a');
    transferButton.href = `/my-tasks/${task.id}/transfer/`; // タスク譲渡画面へのURL
    transferButton.className = 'btn btn-transfer';
    transferButton.textContent = '譲渡';

    // --- 作成した要素を組み立ててページに追加 ---
    buttonContainer.appendChild(backButton);
    buttonContainer.appendChild(returnButton);
    buttonContainer.appendChild(transferButton);

    section.appendChild(title);
    section.appendChild(dueDateItem);
    section.appendChild(assigneeItem);
    section.appendChild(descriptionItem);
    section.appendChild(manualItem);
    section.appendChild(buttonContainer);

    container.appendChild(section);
}

// ページの読み込みが完了した後に実行
document.addEventListener('DOMContentLoaded', () => {
    // HTMLに埋め込まれたJSONデータを取得してパースする
    const taskDataElement = document.getElementById('task-data');
    if (taskDataElement) {
        const taskData = JSON.parse(taskDataElement.textContent);
        // 描画関数を実行
        renderTaskDetail(taskData);
    } else {
        console.error('タスクデータが見つかりません。');
    }
});

