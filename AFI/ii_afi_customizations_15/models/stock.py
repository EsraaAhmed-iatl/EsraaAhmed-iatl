

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


# inheritance to add fields
class StockMove(models.Model):
    _inherit = 'stock.move'

    loc_case = fields.Char(string='Case', related='product_id.loc_case')


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    loc_case = fields.Char(string='Case', related='product_id.loc_case')

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, qty_done, product_uom}, ...}
        """
        aggregated_move_lines = {}

        def get_aggregated_properties(move_line=False, move=False):
            move = move or move_line.move_id
            uom = move_line and move_line.product_uom_id or move.product_uom
            name = move.product_id.display_name
            description = move.description_picking
            loc_case = move_line.move_id.loc_case
            if description == name or description == move.product_id.name:
                description = False
            product = move.product_id
            line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}'
            return (line_key, name, description, uom)

        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids

        for move_line in self:
            line_key, name, description, uom = get_aggregated_properties(move_line=move_line)
            loc_case = move_line.move_id.loc_case
            if line_key not in aggregated_move_lines:
                qty_ordered = move_line.move_id.product_uom_qty
                if backorders:
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                aggregated_move_lines[line_key] = {'name': name,
                                                   'description': description,
                                                   'qty_done': move_line.qty_done,
                                                   'qty_ordered': qty_ordered,
                                                   'loc_case': loc_case,
                                                   'product_uom': uom.name,
                                                   'product': move_line.product_id}
            else:
                aggregated_move_lines[line_key]['qty_done'] += move_line.qty_done

        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_lines.filtered(
            lambda m: m.state == "cancel" and m.product_uom_qty
            and float_is_zero(m.quantity_done, precision_rounding=m.product_uom.rounding)
        ):
            line_key, name, description, uom = get_aggregated_properties(move=empty_move)

            if line_key not in aggregated_move_lines:
                qty_ordered = empty_move.product_uom_qty
                aggregated_move_lines[line_key] = {
                    'name': name,
                    'description': description,
                    'qty_done': False,
                    'qty_ordered': qty_ordered,
                    'loc_case': loc_case,
                    'product_uom': uom.name,
                    'product': empty_move.product_id,
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty

        return aggregated_move_lines
