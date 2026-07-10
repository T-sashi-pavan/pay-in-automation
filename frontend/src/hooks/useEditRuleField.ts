import { useRef } from 'react';
import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';
import { api } from '../services/api';
import { getEditedBy } from '../utils/identity';
import { useNotification } from '../contexts/NotificationContext';
import type { CommissionRule, EditableRuleField, EditableSlabField } from '../types';

type EditTarget =
  | { kind: 'rule'; field: EditableRuleField }
  | { kind: 'slab'; slabId: number; field: EditableSlabField };

export interface EditRuleVariables {
  /** The parent CommissionRule id — used to locate the row in every cached page/search result. */
  ruleId: number;
  target: EditTarget;
  value: string | number | null;
}

interface MutationContext {
  snapshots: [QueryKey, unknown][];
}

const RECORD_QUERY_PREFIXES: QueryKey[] = [['records'], ['globalSearch']];

const patchRow = (old: any, ruleId: number, updater: (r: CommissionRule) => CommissionRule) => {
  if (!old || !Array.isArray(old.records)) return old;
  let changed = false;
  const records = old.records.map((r: CommissionRule) => {
    if (r.id !== ruleId) return r;
    changed = true;
    return updater(r);
  });
  return changed ? { ...old, records } : old;
};

/**
 * Shared editing mutation used by both Dashboard.tsx and CustomiseData.tsx.
 * Optimistically patches every cached ['records', ...] and ['globalSearch', ...]
 * query (predicate-based, since both embed filters/upload id in their key) so an
 * edit made from either page is immediately visible on the other without a refetch.
 *
 * commission_type edits are NOT optimistic — a type flip changes which column
 * set the row renders under (nonSlabColumns vs slabColumns), so the row is left
 * untouched until the server's authoritative cascaded response arrives.
 */
export function useEditRuleField() {
  const queryClient = useQueryClient();
  const { notify } = useNotification();
  const mutationRef = useRef<ReturnType<typeof useMutation<CommissionRule, any, EditRuleVariables, MutationContext>> | null>(null);

  const mutation = useMutation<CommissionRule, any, EditRuleVariables, MutationContext>({
    mutationFn: async (vars) => {
      const editedBy = getEditedBy();
      if (vars.target.kind === 'rule') {
        return api.updateCommissionRuleField(vars.ruleId, vars.target.field, vars.value, editedBy);
      }
      return api.updateSlabDetailField(vars.target.slabId, vars.target.field, vars.value, editedBy);
    },

    onMutate: async (vars) => {
      const isCommissionTypeEdit = vars.target.kind === 'rule' && vars.target.field === 'commission_type';
      if (isCommissionTypeEdit || vars.target.kind === 'slab') {
        // Slab-tier edits render inside an already-open expanded row — skip
        // optimistic top-level row patching for those too, same reasoning.
        return { snapshots: [] };
      }

      for (const prefix of RECORD_QUERY_PREFIXES) {
        await queryClient.cancelQueries({ queryKey: prefix });
      }

      const snapshots: [QueryKey, unknown][] = RECORD_QUERY_PREFIXES.flatMap(
        (prefix) => queryClient.getQueriesData({ queryKey: prefix })
      );

      const field = vars.target.kind === 'rule' ? vars.target.field : null;
      RECORD_QUERY_PREFIXES.forEach((prefix) => {
        queryClient.setQueriesData({ queryKey: prefix }, (old: any) =>
          patchRow(old, vars.ruleId, (r) => (field ? { ...r, [field]: vars.value } : r))
        );
      });

      return { snapshots };
    },

    onError: (err, vars, context) => {
      context?.snapshots.forEach(([key, data]) => {
        queryClient.setQueryData(key, data);
      });
      const detail = err?.response?.data?.detail || err?.message || 'Unable to update record.';
      notify(detail, 'error', {
        label: 'Retry',
        onClick: () => mutationRef.current?.mutate(vars),
      });
    },

    onSuccess: (updatedRule) => {
      RECORD_QUERY_PREFIXES.forEach((prefix) => {
        queryClient.setQueriesData({ queryKey: prefix }, (old: any) =>
          patchRow(old, updatedRule.id, () => updatedRule)
        );
      });
      queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
      notify('Updated successfully', 'success');
    },
  });

  mutationRef.current = mutation;
  return mutation;
}
