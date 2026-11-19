/* Five-column Cyrillic capitals for short display headings. */
const pixelLetters = {
  А:[14,17,17,31,17,17,17], В:[30,17,17,30,17,17,30],
  Г:[31,16,16,16,16,16,16], Д:[14,10,10,10,10,31,17],
  Е:[31,16,16,30,16,16,31], З:[30,1,1,14,1,1,30],
  И:[17,17,19,21,25,17,17], Й:[10,4,17,19,21,25,17],
  К:[17,18,20,24,20,18,17], Л:[15,9,9,9,9,9,17],
  М:[17,27,21,21,17,17,17], Н:[17,17,17,31,17,17,17],
  О:[14,17,17,17,17,17,14], П:[31,17,17,17,17,17,17],
  Р:[30,17,17,30,16,16,16], С:[15,16,16,16,16,16,15],
  Т:[31,4,4,4,4,4,4], У:[17,17,17,15,1,2,28],
  Ф:[4,14,21,21,14,4,4], Х:[17,17,10,4,10,17,17],
  Ч:[17,17,17,15,1,1,1], Ш:[21,21,21,21,21,21,31],
  Ы:[17,17,17,29,21,21,29], Ь:[16,16,16,30,17,17,30],
  Я:[15,17,17,15,5,9,17]
};
function pixelHeading(node) {
  const label = node.textContent;
  const words = label.toUpperCase().split(/\s+/);
  if (words.some(word => [...word].some(letter => !pixelLetters[letter]))) return;
  node.setAttribute('aria-label',label);
  node.replaceChildren();
  for (const word of words) {
    const width = word.length * 6 - 1;
    const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 '+width+' 7');
    svg.setAttribute('aria-hidden','true');
    svg.setAttribute('shape-rendering','crispEdges');
    svg.style.width = width / 7 + 'em';
    const path = document.createElementNS(svg.namespaceURI,'path');
    let pixels = '';
    [...word].forEach((letter,index) => pixelLetters[letter].forEach((row,y) => {
      for (let x=0;x<5;x++) if (row & (16 >> x)) pixels += 'M'+(index*6+x)+' '+y+'h1v1h-1z';
    }));
    path.setAttribute('d',pixels);
    path.setAttribute('fill','currentColor');
    svg.append(path);
    node.append(svg,document.createTextNode(' '));
  }
  node.classList.add('pixel-heading');
}
