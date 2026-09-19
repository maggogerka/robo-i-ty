import { ArrowRight, CheckCircle2, Database, Gauge, Route } from "lucide-react";
import { Link } from "react-router-dom";

const features = [
  {
    icon: Database,
    number: "187",
    label: "уникальных продуктов",
    note: "и 223 строки внедрений/кейсов",
  },
  {
    icon: Gauge,
    number: "3",
    label: "сценария экономики",
    note: "база, покупка и RaaS",
  },
  {
    icon: Route,
    number: "6",
    label: "факторов рейтинга",
    note: "каждый вклад объяснён",
  },
];

export function HomePage() {
  return (
    <div>
      <section className="hero page-wide">
        <div className="hero-copy">
          <div className="eyebrow"><span /> Платформа предынвестиционной оценки</div>
          <h1>От параметров объекта до <em>обоснованного</em> решения по роботизации</h1>
          <p className="lead">
            Сопоставьте реальные условия объекта с каталогом решений, проверьте ограничения и
            оцените экономику — с прозрачными формулами, источниками и допущениями.
          </p>
          <div className="hero-actions">
            <Link to="/demo" className="button button-primary">
              Открыть демо склада <ArrowRight size={18} />
            </Link>
            <Link to="/catalog" className="button button-secondary">Изучить каталог</Link>
          </div>
          <p className="trust-line"><CheckCircle2 size={17} /> Без регистрации для знакомства · фиксированный демосценарий</p>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="visual-grid" />
          <div className="route-line route-one" />
          <div className="route-line route-two" />
          <div className="robot robot-one"><span>R1</span></div>
          <div className="robot robot-two"><span>R2</span></div>
          <div className="metric-float metric-a"><b>82,4</b><span>рейтинг</span></div>
          <div className="metric-float metric-b"><b>0,9 года</b><span>окупаемость</span></div>
          <div className="zone zone-a">Приёмка</div>
          <div className="zone zone-b">Комплектация</div>
        </div>
      </section>

      <section className="proof page-wide" aria-label="Масштаб данных">
        {features.map(({ icon: Icon, number, label, note }) => (
          <article key={label}>
            <Icon />
            <div><strong>{number}</strong><span>{label}</span><small>{note}</small></div>
          </article>
        ))}
      </section>

      <section className="how page-wide">
        <div>
          <p className="section-kicker">Как принимается решение</p>
          <h2>Не чёрный ящик, а проверяемая цепочка</h2>
        </div>
        <ol>
          <li><span>01</span><div><b>Опишите объект</b><p>Формы строятся из 138 параметров исходного XLSX.</p></div></li>
          <li><span>02</span><div><b>Отсейте невозможное</b><p>Жёсткие ограничения отделены от рейтинга.</p></div></li>
          <li><span>03</span><div><b>Сравните варианты</b><p>Видны вклад факторов, пробелы данных и допущения.</p></div></li>
          <li><span>04</span><div><b>Проверьте экономику</b><p>CAPEX, OPEX, TCO, ROI и чувствительность по трём факторам.</p></div></li>
        </ol>
      </section>
    </div>
  );
}
