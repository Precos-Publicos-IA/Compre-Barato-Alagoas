import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config.dart';

/// In-app Política de Privacidade e Termos (pt-BR). Rendered in-app so it works
/// offline and identically on Android and web. A static mirror is also served at
/// `/privacy.html` for a public, canonical URL (#377).
class PolicyScreen extends StatelessWidget {
  const PolicyScreen({super.key});

  static final Uri webPrivacyUri =
      Uri.parse('${AppConfig.webBaseUrl}/privacy.html');

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Privacidade e Termos')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Política de Privacidade e Termos de Uso',
                style: text.titleLarge),
            const SizedBox(height: 4),
            Text('Versão ${AppConfig.policyVersion}',
                style: text.bodySmall),
            const SizedBox(height: 16),
            const _Section(
              'Quem somos',
              'O Compre Barato Alagoas é um app gratuito e de código aberto que '
                  'compara preços a partir de dados públicos de notas fiscais '
                  '(NFC-e) divulgados pela SEFAZ-AL. Ele ajuda você a encontrar '
                  'os lugares mais baratos para sua lista de compras.',
            ),
            const _Section(
              'O que fica só no seu aparelho',
              'Suas listas de compras e o histórico recente (últimas buscas, '
                  'em texto simples nas preferências do aparelho) ficam guardados '
                  'no próprio aparelho — inclusive em dispositivos compartilhados '
                  'da família, até você limpar em Configurações. As lojas que '
                  'você marca como favoritas ou oculta também ficam só no '
                  'aparelho — não vão para o servidor. Sua localização é usada '
                  'apenas no momento da busca, para encontrar lojas perto de '
                  'você — não guardamos seu histórico de localização.',
            ),
            const _Section(
              'Identificação sem login',
              'Para oferecer recursos que normalmente exigiriam uma conta (como '
                  'salvar suas listas na nuvem e, no futuro, avisos de promoção), '
                  'o app cria um identificador aleatório para o aparelho. Ele não '
                  'contém seu nome, e-mail ou telefone, e fica guardado de forma '
                  'segura no aparelho. Não há login e não há portabilidade: se '
                  'você trocar, perder ou redefinir o aparelho, esses dados se '
                  'perdem.',
            ),
            const _Section(
              'Medição anônima de uso',
              'Para saber quantas pessoas usam o app e melhorá-lo, fazemos uma '
                  'contagem anônima e agregada de uso (por exemplo, quantos '
                  'aparelhos diferentes buscam por dia). Para isso o app usa um '
                  'identificador aleatório próprio dessa medição — separado do '
                  'identificador de "salvar na nuvem" e nunca ligado às suas '
                  'listas. Ele não contém seu nome, e-mail ou telefone. No '
                  'servidor, esse dado vira apenas um número total (uma '
                  'estimativa de quantos aparelhos), de forma anonimizada, sem '
                  'guardar um registro por aparelho e sem traçar perfil. Não '
                  'compartilhamos com terceiros. A base legal é o legítimo '
                  'interesse (LGPD). Você pode desligar quando quiser em '
                  'Configurações → "Estatísticas anônimas de uso"; ao desligar, '
                  'o identificador de medição é esquecido no aparelho.',
            ),
            const _Section(
              'Quando guardamos algo no servidor',
              'Só guardamos dados ligados ao seu aparelho no servidor se você '
                  'ativar "Salvar minhas listas na nuvem". A base legal é o seu '
                  'consentimento (LGPD). Nesse caso, associamos suas listas ao '
                  'identificador do aparelho. Links compartilhados guardam '
                  'apenas os itens da lista, sem identificar quem criou. A '
                  'medição anônima de uso, descrita acima, é a única exceção: '
                  'ela não fica ligada ao seu aparelho — vira só um total '
                  'agregado.',
            ),
            const _Section(
              'Por quanto tempo guardamos (retenção)',
              'Se você consentiu em salvar listas na nuvem, o registro do '
                  'aparelho no servidor pode expirar após cerca de 90 dias sem '
                  'uso (sem novas buscas/consentimento/atualizações). Links '
                  'compartilhados (/abrir/…) podem expirar após cerca de 30 dias '
                  'sem acesso, com limite máximo de cerca de 90 dias desde a '
                  'criação (abrir o link renova o prazo ocioso, mas não além '
                  'desse teto). Desativar "Salvar minhas listas na nuvem" apaga '
                  'de imediato os dados do aparelho no servidor, sem esperar o prazo.',
            ),
            const _Section(
              'Melhoria da busca (termos sem identificar você)',
              'Para melhorar correspondências de produtos (ex.: termos vagos '
                  'para nomes mais úteis na SEFAZ), o servidor pode guardar, de '
                  'forma agregada e sem ligar ao seu aparelho, associações entre '
                  'o que as pessoas digitam e termos de busca que funcionaram. '
                  'Esses registros podem permanecer por até cerca de 180 dias e '
                  'não entraram no apagamento do consentimento de nuvem (não são '
                  'dados pessoais do seu aparelho). A base legal é o legítimo '
                  'interesse (LGPD), com a mesma possibilidade de desligar a '
                  'medição anônima de uso em Configurações quando aplicável ao '
                  'fluxo de busca.',
            ),
            const _Section(
              'Seus direitos (LGPD)',
              'Você pode retirar o consentimento e apagar tudo o que guardamos '
                  'no servidor a qualquer momento, desativando "Salvar minhas '
                  'listas na nuvem" — isso apaga, de imediato, os dados '
                  'associados ao seu aparelho. Para apagar só o histórico recente '
                  'local, use "Limpar listas recentes" em Configurações.',
            ),
            const _Section(
              'Avisos de promoção (futuro)',
              'Quando os avisos de promoção forem lançados, pediremos um '
                  'consentimento específico. O envio poderá usar serviços de '
                  'notificação de terceiros (por exemplo, Google Firebase Cloud '
                  'Messaging), o que pode envolver transferência internacional '
                  'de dados. Isso será detalhado antes da ativação.',
            ),
            const _Section(
              'Contato',
              'Dúvidas sobre privacidade podem ser enviadas pelo repositório '
                  'público do projeto (Preços Públicos IA). A avaliação de '
                  'legítimo interesse da medição de uso está publicada na '
                  'documentação do projeto.',
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: () => launchUrl(
                webPrivacyUri,
                mode: LaunchMode.externalApplication,
              ),
              icon: const Icon(Icons.open_in_browser),
              label: const Text('Abrir política no navegador (privacy.html)'),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section(this.title, this.body);
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: text.titleMedium),
          const SizedBox(height: 4),
          Text(body, style: text.bodyMedium?.copyWith(height: 1.4)),
        ],
      ),
    );
  }
}
