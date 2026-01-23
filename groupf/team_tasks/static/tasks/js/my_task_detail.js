// ★★★デバッグを強化したバージョン★★★

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOMが読み込まれました。スクリプトを開始します。");

    const taskDataElement = document.getElementById('task-data');
    
    // 1. データが埋め込まれたscriptタグが見つかるか？
    if (taskDataElement) {
        console.log("script#task-data が見つかりました。");
        
        try {
            // 2. JSONデータを正しくパースできるか？
            const taskData = JSON.parse(taskDataElement.textContent);
            console.log("JSONデータのパースに成功しました:", taskData);

            // 3. データの中身は期待通りか？
            if (taskData && taskData.title) {
                console.log("タスクタイトル:", taskData.title);
                renderTaskDetail(taskData);
            } else {
                console.error("パース後のデータが空か、titleプロパティがありません。");
            }
        } catch (e) {
            console.error('JSONデータの解析中にエラーが発生しました:', e);
            console.error('scriptタグの内容:', taskDataElement.textContent);
        }
    } else {
        console.error('script#task-data が見つかりませんでした。HTMLを確認してください。');
    }
});

function renderTaskDetail(task) {
    const container = document.getElementById('task-detail-container');
    if (!container) {
        console.error("描画コンテナ #task-detail-container が見つかりません。");
        return;
    }
    // 描画前にコンテナを空にする
    container.innerHTML = '';

    // ... (以降の描画処理は前回と同じ) ...
    const section = document.createElement('section');
    section.className = 'task-detail-section';
    
    // ★★★念のため、各プロパティの値もコンソールに出力してみる★★★
    console.log("描画データ:", {
        title: task.title,
        due_date: task.due_date,
        assignee: task.assignee,
        description: task.description,
        manual: task.manual
    });
    
    const title = document.createElement('h1');
    title.className = 'task-title';
    title.textContent = task.title || '（タイトルなし）'; // undefinedの場合のフォールバックを追加

    const createDetailItem = (label, value) => {
        const div = document.createElement('div');
        div.className = 'detail-item';
        const strong = document.createElement('strong');
        strong.textContent = `${label}：`;
        // undefinedなら空文字を表示するようにする
        const text = document.createTextNode(value || ''); 
        div.appendChild(strong);
        div.appendChild(text);
        return div;
    };
    
    const dueDateItem = createDetailItem('期限', task.due_date);
    const assigneeItem = createDetailItem('担当者', task.assignee);
    const descriptionItem = createDetailItem('詳細', task.description);
    const manualItem = createDetailItem('マニュアル', task.manual);

    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'button-container';

    // (ボタンの作成処理は省略)
    const backButton = document.createElement('a');
    backButton.href = '/my-tasks';
    backButton.className = 'btn btn-back';
    backButton.textContent = '戻る';

    const returnButton = document.createElement('button');
    returnButton.type = 'button';
    returnButton.className = 'btn btn-return';
    returnButton.textContent = '返却';
    
    const transferButton = document.createElement('a');
    transferButton.href = `/my-tasks/${task.id}/transfer/`;
    transferButton.className = 'btn btn-transfer';
    transferButton.textContent = '譲渡';


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
    console.log("タスク詳細の描画が完了しました。");
}