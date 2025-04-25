// static/js/calculations.js
document.addEventListener('DOMContentLoaded', function() {
    const presetsById = {};
    olapPresets.forEach(p => {
        presetsById[p.id] = p;
    });

    const container = document.getElementById('calculation-rows-container');
    const template = document.getElementById('calculation-row-template');
    const addRowButton = document.getElementById('add-calculation-row');
    const saveForm = document.getElementById('save-calculations-form');
    const calculationsInput = document.getElementById('calculations-json-input');

    // --- Функции ---

    // Функция для заполнения полей отчета (только aggregateFields)
    function populateFieldSelect(reportSelect, fieldSelect) {
        const reportId = reportSelect.value;
        fieldSelect.innerHTML = '<option value="" selected disabled>Выберите поле...</option>'; // Очистка
        fieldSelect.disabled = true;

        if (reportId && presetsById[reportId]) {
            const preset = presetsById[reportId];
            // Используем ТОЛЬКО aggregateFields для вычислений
            const fields = preset.aggregateFields || [];

            if (fields.length > 0) {
                fields.forEach(field => {
                    const option = document.createElement('option');
                    option.value = field;
                    option.textContent = field; // Отображаем техническое имя
                    fieldSelect.appendChild(option);
                });
                fieldSelect.disabled = false;
            } else {
                 fieldSelect.innerHTML = '<option value="" selected disabled>Нет аггрег. полей</option>';
            }
        }
    }

    // Функция создания новой строки конструктора
    function createCalculationRow(data = {}) {
        const clone = template.content.cloneNode(true);
        const rowElement = clone.querySelector('.calculation-row');

        // Заполняем селекты отчетов
        const reportSelects = clone.querySelectorAll('.calc-report-select');
        reportSelects.forEach(select => {
            olapPresets.forEach(preset => {
                const option = document.createElement('option');
                option.value = preset.id;
                option.textContent = preset.name || preset.id; // Отображаем имя пресета
                select.appendChild(option);
            });
        });

        // Находим элементы управления в клоне
        const idInput = clone.querySelector('.calc-id');
        const report1Select = clone.querySelector('.operand1-report');
        const field1Select = clone.querySelector('.operand1-field');
        const operationSelect = clone.querySelector('.calc-operation');
        const report2Select = clone.querySelector('.operand2-report');
        const field2Select = clone.querySelector('.operand2-field');
        const targetCellInput = clone.querySelector('.calc-target-cell');
        const removeButton = clone.querySelector('.remove-calc-row');

        // Устанавливаем значения из данных (если загружаем сохраненные)
        idInput.value = data.id || ''; // Устанавливаем ID, если он есть
        report1Select.value = data.operand1_report_id || '';
        operationSelect.value = data.operation || '+';
        report2Select.value = data.operand2_report_id || '';
        targetCellInput.value = data.target_cell || '';

        // Заполняем поля для выбранных отчетов (если они есть)
        if (data.operand1_report_id) {
            populateFieldSelect(report1Select, field1Select);
            field1Select.value = data.operand1_field_name || '';
        }
        if (data.operand2_report_id) {
            populateFieldSelect(report2Select, field2Select);
            field2Select.value = data.operand2_field_name || '';
        }


        // Добавляем обработчики событий для новой строки
        report1Select.addEventListener('change', () => populateFieldSelect(report1Select, field1Select));
        report2Select.addEventListener('change', () => populateFieldSelect(report2Select, field2Select));
        removeButton.addEventListener('click', () => rowElement.remove());

        container.appendChild(clone);
    }

    // --- Инициализация ---

    // Загружаем сохраненные определения при загрузке страницы
    if (savedCalculations && savedCalculations.length > 0) {
        savedCalculations.forEach(calcData => createCalculationRow(calcData));
    } else {
        // Добавляем одну пустую строку, если нет сохраненных
        createCalculationRow();
    }

    // Обработчик кнопки "Добавить строку"
    addRowButton.addEventListener('click', () => createCalculationRow());

    // Обработчик отправки формы сохранения
    saveForm.addEventListener('submit', function(event) {
        const rows = container.querySelectorAll('.calculation-row');
        const calculationsData = [];
        let isValid = true;

        rows.forEach(row => {
            const id = row.querySelector('.calc-id').value;
            const report1 = row.querySelector('.operand1-report').value;
            const field1 = row.querySelector('.operand1-field').value;
            const operation = row.querySelector('.calc-operation').value;
            const report2 = row.querySelector('.operand2-report').value;
            const field2 = row.querySelector('.operand2-field').value;
            const targetCell = row.querySelector('.calc-target-cell').value;

            // Простая валидация на клиенте
            if (!report1 || !field1 || !operation || !report2 || !field2 || !targetCell) {
                 // Подсветить незаполненные поля или показать сообщение
                 console.warn("Строка не заполнена полностью, пропускается при сохранении:", row);
                 // Можно добавить класс ошибки к row
                 // isValid = false; // Раскомментируйте, если хотите прервать сохранение при неполных строках
                 return; // Пропускаем эту строку, если она не валидна
            }

            calculationsData.push({
                id: id, // Передаем существующий ID
                operand1_report_id: report1,
                operand1_field_name: field1,
                operation: operation,
                operand2_report_id: report2,
                operand2_field_name: field2,
                target_cell: targetCell
            });
        });

        /* if (!isValid) {
             event.preventDefault(); // Отменяем отправку формы
             alert("Пожалуйста, заполните все поля во всех строках расчетов или удалите незаполненные строки.");
             return;
        } */

        // Помещаем собранные данные в скрытое поле в виде JSON
        calculationsInput.value = JSON.stringify(calculationsData);

        // Форма отправится стандартным образом
    });

    // Установка сегодняшней даты по умолчанию для полей дат калькулятора
    const today = new Date().toISOString().split('T')[0];
    const startDateCalc = document.getElementById('start_date_calc');
    const endDateCalc = document.getElementById('end_date_calc');
    if (startDateCalc && !startDateCalc.value) startDateCalc.value = today;
    if (endDateCalc && !endDateCalc.value) endDateCalc.value = today;

    // Открытие нужной секции, если есть якорь в URL
    if (window.location.hash) {
        const element = document.querySelector(window.location.hash);
        if (element && element.tagName === 'DETAILS') {
            element.open = true;
        }
    }

});