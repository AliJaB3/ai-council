"""Inject external evidence when deliberation is uncertain or contested."""
class EvidencePump:
    @staticmethod
    def should_pump(entropy, contested_claims_count, threshold_entropy=0.8):
        return entropy > threshold_entropy or contested_claims_count > 0

    def inject(self, query, gateway, tool_name, args):
        arguments = dict(args)
        arguments.setdefault('query', query)
        return gateway.call_tool(tool_name, arguments)
