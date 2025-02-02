/** @odoo-module */

import { registry } from '@web/core/registry';
import { StateSelectionField } from '@web/views/fields/state_selection/state_selection_field';

import { STATUS_COLORS, STATUS_COLOR_PREFIX } from '../../utils/tec_utils';

export class TecStateSelectionField extends StateSelectionField {
    setup() {
        super.setup();
        this.colorPrefix = STATUS_COLOR_PREFIX;
        this.colors = STATUS_COLORS;
    }

    /**
     * @override
     */
    get showLabel() {
        return !this.props.hideLabel;
    }

    /**
     * @override
     */
    get options() {
        return super.options.filter(o => o[0] !== 'to_define');
    }
}

registry.category('fields').add('kanban.tec_state_selection', TecStateSelectionField);
